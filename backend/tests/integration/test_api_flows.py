"""
The whole app over HTTP against real Postgres: routers, dependency wiring,
the anti-corruption adapters between modules, repositories, real SQL and
the data seeded by the migrations. Only the DB session is swapped for the
per-test transactional one.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.iam.infraestructure.security.login_rate_limiter import LoginRateLimiter
from app.iam.presentation.http.dependencies import get_login_rate_limiter
from app.main import app
from app.recipes.infraestructure.persistence.models.recipe_section_model import RecipeSectionModel
from app.shared.database.session import get_db_session

PASSWORD = "Secret123"


@pytest.fixture
async def client(db_session):
    async def test_session():
        yield db_session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_login_rate_limiter] = lambda: LoginRateLimiter(5, 900)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()


async def sign_up(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/v1/auth/register", json={"email": email, "password": PASSWORD, "full_name": email})
    assert response.status_code == 201, response.text
    response = await client.post("/v1/auth/login", data={"username": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def ok(response, status: int = 200):
    assert response.status_code == status, response.text
    return response.json() if response.content else None


@pytest.fixture
async def catalog(client):
    """Ids of seeded rows, looked up through the public API."""
    headers = await sign_up(client, "catalog@example.com")
    # Lookups below use the seeded Spanish names.
    await ok(await client.patch("/v1/users/me/language", json={"preferred_language": "es"}, headers=headers))
    units = {u["abbreviation"]: u["id"] for u in await ok(await client.get("/v1/units", headers=headers))}

    async def ingredient(name):
        page = await ok(await client.get("/v1/ingredients", params={"q": name}, headers=headers))
        return next(i["id"] for i in page["items"] if i["name"] == name)

    categories = await ok(await client.get("/v1/recipe-categories", headers=headers))
    difficulties = await ok(await client.get("/v1/difficulties", headers=headers))
    tags = await ok(await client.get("/v1/recipe-tags", headers=headers))
    equipment = await ok(await client.get("/v1/equipment", params={"limit": 100}, headers=headers))
    return {
        "units": units,
        "flour": await ingredient("Harina todo uso (0000)"),
        "butter": await ingredient("Mantequilla / Manteca"),
        "egg_white": await ingredient("Huevo, clara"),
        "category": categories[0]["id"],
        "difficulty": difficulties[0]["id"],
        "tags": [t["id"] for t in tags],
        "equipment": [e["id"] for e in equipment["items"]],
    }


def recipe_body(catalog, title="Brownies", ingredients=None, equipment=None, **extra):
    units = catalog["units"]
    return {
        "title": title,
        "is_public": True,
        "category_id": catalog["category"],
        "difficulty_id": catalog["difficulty"],
        "tag_ids": catalog["tags"][:2],
        "ingredients": ingredients
        if ingredients is not None
        else [
            {"ingredient_id": catalog["flour"], "quantity": "2", "unit_id": units["cup"]},
            {"ingredient_id": catalog["butter"], "quantity": "100", "unit_id": units["g"]},
        ],
        "equipment": [{"equipment_id": e} for e in (equipment if equipment is not None else catalog["equipment"][:1])],
        "steps": [
            {"instructions": "Mezclar"},
            {"instructions": "Hornear", "timer_seconds": 1800},
            {"instructions": "Enfriar"},
        ],
        **extra,
    }


class TestSeedsAndConverter:

    async def test_seeded_catalogs(self, catalog):
        assert set(catalog["units"]) == {"g", "kg", "oz", "ml", "l", "cup", "tbsp", "tsp", "u"}
        assert len(catalog["tags"]) == 28

    @pytest.mark.parametrize(
        "quantity, source, target, expected",
        [
            ("2", "cup", "g", "250"),  # seeded figure: 1 cup = 125 g
            ("1", "l", "g", "528.34"),  # no per-litre figure: derived from the cup one
            ("1", "kg", "g", "1000"),
        ],
    )
    async def test_converter(self, client, catalog, quantity, source, target, expected):
        headers = await sign_up(client, "cook@example.com")
        units = catalog["units"]

        result = await ok(
            await client.post(
                "/v1/converter",
                json={"quantity": quantity, "from_unit_id": units[source], "to_unit_id": units[target], "ingredient_id": catalog["flour"]},
                headers=headers,
            )
        )

        assert round(Decimal(str(result["converted_quantity"])), 2) == Decimal(expected)

    async def test_pantry_round_trip(self, client, catalog):
        headers = await sign_up(client, "pantry@example.com")
        body = {"ingredient_id": catalog["flour"], "quantity": "1", "unit_id": catalog["units"]["kg"]}

        await ok(await client.put("/v1/pantry", json=body, headers=headers))
        await ok(await client.put("/v1/pantry", json={**body, "quantity": "2"}, headers=headers))
        pantry = await ok(await client.get("/v1/pantry", headers=headers))

        assert [(p["ingredient"]["id"], Decimal(str(p["quantity"]))) for p in pantry] == [(catalog["flour"], Decimal("2"))]
        await ok(await client.delete(f"/v1/pantry/{catalog['flour']}", headers=headers), 204)
        await ok(await client.delete("/v1/pantry/garbage", headers=headers), 204)
        assert await ok(await client.get("/v1/pantry", headers=headers)) == []


class TestRecipeLifecycle:

    async def test_create_edit_photos_and_reorder_steps(self, client, catalog):
        headers = await sign_up(client, "author@example.com")
        recipe = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=headers), 201)
        recipe_id = recipe["id"]
        mix, bake, cool = (s["id"] for s in recipe["steps"])

        # Step photo on "Hornear", then reverse the steps and drop "Mezclar":
        # renumbering in place relies on the deferred UNIQUE(recipe_id, step_number).
        await ok(
            await client.post(
                f"/v1/recipes/{recipe_id}/photos",
                json={"photo_type": "step", "photo_url": "https://img/bake.jpg", "step_id": bake},
                headers=headers,
            ),
            201,
        )
        mix_photo = await ok(
            await client.post(
                f"/v1/recipes/{recipe_id}/photos",
                json={"photo_type": "step", "photo_url": "https://img/mix.jpg", "step_id": mix},
                headers=headers,
            ),
            201,
        )
        steps = await ok(
            await client.put(
                f"/v1/recipes/{recipe_id}/steps",
                json={"steps": [{"id": cool, "instructions": "Enfriar"}, {"id": bake, "instructions": "Hornear 25'"}]},
                headers=headers,
            )
        )

        assert [(s["id"], s["step_number"]) for s in steps["steps"]] == [(cool, 1), (bake, 2)]
        assert steps["steps"][1]["photo"]["photo_url"] == "https://img/bake.jpg"
        photos = await ok(await client.get(f"/v1/recipes/{recipe_id}/photos", headers=headers))
        assert mix_photo["id"] not in [p["id"] for p in photos]

        # Reload from the database: what was persisted, not what the response echoed.
        stored = await ok(await client.get(f"/v1/recipes/{recipe_id}", headers=headers))
        assert [s["instructions"] for s in stored["steps"]] == ["Enfriar", "Hornear 25'"]
        assert [i["position"] for i in stored["ingredients"]] == [1, 2]
        assert len(stored["tags"]) == 2

    async def test_cover_photos_limit_and_order(self, client, catalog):
        headers = await sign_up(client, "photos@example.com")
        recipe_id = (await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=headers), 201))["id"]
        covers = [
            (await ok(
                await client.post(
                    f"/v1/recipes/{recipe_id}/photos", json={"photo_type": "cover", "photo_url": f"https://img/{n}.jpg"}, headers=headers
                ),
                201,
            ))["id"]
            for n in range(3)
        ]

        too_many = await client.post(
            f"/v1/recipes/{recipe_id}/photos", json={"photo_type": "cover", "photo_url": "https://img/4.jpg"}, headers=headers
        )
        assert too_many.status_code == 409

        reordered = await ok(
            await client.put(f"/v1/recipes/{recipe_id}/photos/cover-order", json={"photo_ids": covers[::-1]}, headers=headers)
        )
        assert [p["id"] for p in reordered] == covers[::-1]

    async def test_visibility_ownership_and_soft_delete(self, client, catalog):
        author = await sign_up(client, "owner@example.com")
        stranger = await sign_up(client, "stranger@example.com")
        public_id = (await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=author), 201))["id"]
        private_id = (
            await ok(await client.post("/v1/recipes", json=recipe_body(catalog, "Secreta", is_public=False), headers=author), 201)
        )["id"]

        assert (await client.get(f"/v1/recipes/{private_id}", headers=stranger)).status_code == 404
        assert (await client.patch(f"/v1/recipes/{public_id}", json={"title": "x"}, headers=stranger)).status_code == 403
        search = await ok(await client.get("/v1/recipes", params={"ingredient_ids": catalog["flour"].upper()}, headers=stranger))
        assert [r["id"] for r in search["items"]] == [public_id]

        await ok(await client.delete(f"/v1/recipes/{public_id}", headers=author), 204)
        assert (await client.get(f"/v1/recipes/{public_id}", headers=author)).status_code == 404
        assert (await ok(await client.get("/v1/recipes/mine", headers=author)))["total"] == 1

    async def test_unknown_references_are_404_not_500(self, client, catalog):
        headers = await sign_up(client, "refs@example.com")
        bad_unit = recipe_body(catalog, ingredients=[{"ingredient_id": catalog["flour"], "quantity": "1", "unit_id": catalog["flour"]}])

        response = await client.post("/v1/recipes", json=bad_unit, headers=headers)

        assert response.status_code == 404
        assert (await ok(await client.get("/v1/recipes/mine", headers=headers)))["total"] == 0


class TestEnglishBase:
    """English is the base: stable codes are English and the seeded catalog was originally written in English."""

    async def test_seeded_codes_and_base_language(self, client, catalog, db_session):
        headers = await sign_up(client, "base@example.com")

        categories = await ok(await client.get("/v1/categories", headers=headers))
        assert {c["name"] for c in categories} == {
            "flour", "sugar", "sweetener", "fat", "dairy", "leavener", "fruit", "nut", "spice", "extract", "other"
        }
        equipment = await ok(await client.get("/v1/equipment", params={"limit": 100}, headers=headers))
        assert {e["equipment_type"] for e in equipment["items"]} == {"mold", "utensil", "appliance", "other"}
        tags = await ok(await client.get("/v1/recipe-tags", headers=headers))
        assert {t["group"] for t in tags} == {"flavor", "diet", "technique", "time", "celebrations"}
        assert (await client.get("/v1/recipe-tags", params={"group": "sabor"}, headers=headers)).status_code == 422

        # Every seeded row has both languages and was originally written in English.
        for table in ("ingredients", "ingredient_categories", "equipment", "recipe_categories", "difficulties", "units", "tags"):
            rows = (await db_session.execute(text(f"SELECT DISTINCT name_language FROM {table}"))).scalars().all()
            assert rows == ["en"], table

    async def test_new_names_fall_back_to_english_when_the_creator_has_no_language(self, client, catalog, db_session):
        headers = await sign_up(client, "fallback@example.com")
        created = await ok(await client.post("/v1/ingredients", json={"name": "Cardamom"}, headers=headers), 201)
        row = (await db_session.execute(text("SELECT name_language FROM ingredients WHERE id = :id"), {"id": created["id"]})).scalar_one()
        assert row == "en"  # the register default; a Spanish speaker's names are stored as "es" (see the other tests)


class TestSynonyms:
    """A name may list regional synonyms ("Mantequilla / Manteca"); any of them is the same ingredient."""

    async def test_search_finds_it_by_any_word_and_a_synonym_is_not_a_new_ingredient(self, client, catalog):
        spanish = await sign_up(client, "synonyms@example.com")
        await ok(await client.patch("/v1/users/me/language", json={"preferred_language": "es"}, headers=spanish))

        for query in ("manteca", "MANTEQUILLA", "butter"):
            page = await ok(await client.get("/v1/ingredients", params={"q": query}, headers=spanish))
            assert "Mantequilla / Manteca" in [item["name"] for item in page["items"]], query

        # Either word is already taken ...
        for name in ("Manteca", "mantequilla", "MANTEQUILLA / manteca"):
            assert (await client.post("/v1/ingredients", json={"name": name}, headers=spanish)).status_code == 409, name
        # ... but a longer name that merely starts with it is a different ingredient (and exists already).
        page = await ok(await client.get("/v1/ingredients", params={"q": "mantequilla de mani"}, headers=spanish))
        assert [item["name"] for item in page["items"]] == ["Mantequilla de maní"]
        assert (await client.post("/v1/ingredients", json={"name": "Mantequilla de cacao"}, headers=spanish)).status_code == 201


class TestImageReferences:
    """The clean-up sweep reads every table that stores an image URL (real SQL)."""

    async def test_every_stored_url_is_found_including_copies_and_deleted_recipes(self, client, catalog, db_session):
        from app.media.infrastructure.sql_image_references import SqlImageReferences

        author = await sign_up(client, "refs-author@example.com")
        fan = await sign_up(client, "refs-fan@example.com")
        await ok(await client.patch("/v1/users/me/profile", json={"avatar_url": "https://cdn/avatar.webp"}, headers=author))
        recipe = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=author), 201)
        await ok(await client.post(f"/v1/recipes/{recipe['id']}/photos", json={"photo_type": "cover", "photo_url": "https://cdn/cover.webp"}, headers=author), 201)
        await ok(
            await client.post(
                f"/v1/recipes/{recipe['id']}/photos",
                json={"photo_type": "step", "photo_url": "https://cdn/step.webp", "step_id": recipe["steps"][0]["id"]},
                headers=author,
            ),
            201,
        )
        # A copy keeps the same URLs, and a preparation snapshots them: both still "use" the files.
        await ok(await client.post(f"/v1/recipes/{recipe['id']}/personalizations", headers=fan), 201)
        await ok(await client.post("/v1/preparations", json={"recipe_id": recipe["id"]}, headers=fan), 201)

        urls = await SqlImageReferences(db_session).urls()
        assert urls == {"https://cdn/avatar.webp", "https://cdn/cover.webp", "https://cdn/step.webp"}

        # Deleting the recipe is logical: its photos stay referenced (and so are not swept) until they are removed.
        await ok(await client.delete(f"/v1/recipes/{recipe['id']}", headers=author), 204)
        assert "https://cdn/cover.webp" in await SqlImageReferences(db_session).urls()


class TestRecipeSections:
    """Groups ("Masa choux", "Manjar") through HTTP, real SQL and the preparation snapshot."""

    @staticmethod
    def grouped_body(catalog):
        units = catalog["units"]
        flour, butter, egg = catalog["flour"], catalog["butter"], catalog["egg_white"]
        return recipe_body(
            catalog,
            "Profiteroles",
            ingredients=[
                {"ingredient_id": flour, "quantity": "1", "unit_id": units["cup"], "section": "Masa choux"},
                {"ingredient_id": butter, "quantity": "100", "unit_id": units["g"], "section": "masa choux"},
                {"ingredient_id": egg, "quantity": "3", "unit_id": units["u"], "section": "Manjar"},
            ],
            steps=[
                {"instructions": "Hervir", "section": "Masa choux"},
                {"instructions": "Batir", "section": "Manjar"},
            ],
        )

    async def test_create_read_edit_and_drop_sections(self, client, catalog, db_session):
        headers = await sign_up(client, "sections@example.com")
        created = await ok(await client.post("/v1/recipes", json=self.grouped_body(catalog), headers=headers), 201)
        recipe_id = created["id"]

        # Reloaded from the database: one section per name, shared by lines and steps.
        stored = await ok(await client.get(f"/v1/recipes/{recipe_id}", headers=headers))
        assert [i["section"] for i in stored["ingredients"]] == ["Masa choux", "Masa choux", "Manjar"]
        assert [s["section"] for s in stored["steps"]] == ["Masa choux", "Manjar"]
        assert stored["ingredients"][0]["section_id"] == stored["ingredients"][1]["section_id"]
        assert stored["ingredients"][0]["section_id"] == stored["steps"][0]["section_id"]

        # Renaming "Manjar" in the ingredients only: the steps still use it, so both groups exist
        # until the steps follow (the editor sends both when a group is renamed).
        units = catalog["units"]
        moved = [
            {"ingredient_id": catalog["flour"], "quantity": "1", "unit_id": units["cup"], "section": "Masa choux"},
            {"ingredient_id": catalog["egg_white"], "quantity": "3", "unit_id": units["u"], "section": "Crema"},
        ]
        after = await ok(await client.put(f"/v1/recipes/{recipe_id}/ingredients", json={"ingredients": moved}, headers=headers))
        assert [i["section"] for i in after["ingredients"]] == ["Masa choux", "Crema"]
        steps = [{"instructions": "Hervir", "section": "Masa choux"}, {"instructions": "Batir", "section": "Crema"}]
        after = await ok(await client.put(f"/v1/recipes/{recipe_id}/steps", json={"steps": steps}, headers=headers))
        assert [s["section"] for s in after["steps"]] == ["Masa choux", "Crema"]

        # No line uses "Manjar" any more: it is gone from the database, not just from the response.
        rows = await db_session.execute(select(RecipeSectionModel.name).where(RecipeSectionModel.recipe_id == uuid.UUID(recipe_id)))
        assert sorted(rows.scalars()) == ["Crema", "Masa choux"]

    async def test_grouping_rules_are_400s(self, client, catalog):
        headers = await sign_up(client, "rules@example.com")
        units = catalog["units"]

        def line(section):
            return {"ingredient_id": catalog["flour"], "quantity": "1", "unit_id": units["g"], "section": section}

        scattered = recipe_body(catalog, ingredients=[line("A"), line("B"), line("A")])
        assert (await client.post("/v1/recipes", json=scattered, headers=headers)).status_code == 400
        ungrouped_last = recipe_body(catalog, ingredients=[line("A"), line(None)])
        assert (await client.post("/v1/recipes", json=ungrouped_last, headers=headers)).status_code == 400
        too_long = recipe_body(catalog, ingredients=[line("x" * 101)])
        assert (await client.post("/v1/recipes", json=too_long, headers=headers)).status_code == 422

    async def test_personalization_and_preparation_keep_the_groups(self, client, catalog):
        author = await sign_up(client, "chef-sections@example.com")
        fan = await sign_up(client, "fan-sections@example.com")
        original = await ok(await client.post("/v1/recipes", json=self.grouped_body(catalog), headers=author), 201)

        copy = await ok(await client.post(f"/v1/recipes/{original['id']}/personalizations", headers=fan), 201)
        assert [i["section"] for i in copy["ingredients"]] == ["Masa choux", "Masa choux", "Manjar"]
        assert copy["ingredients"][0]["section_id"] != original["ingredients"][0]["section_id"]
        # Emptying the copy's groups leaves the original alone.
        await ok(await client.put(f"/v1/recipes/{copy['id']}/steps", json={"steps": [{"instructions": "Todo"}]}, headers=fan))
        await ok(
            await client.put(
                f"/v1/recipes/{copy['id']}/ingredients",
                json={"ingredients": [{"ingredient_id": catalog["flour"], "quantity": "1", "unit_id": catalog["units"]["g"]}]},
                headers=fan,
            )
        )
        assert [i["section"] for i in (await ok(await client.get(f"/v1/recipes/{original['id']}", headers=author)))["ingredients"]] == [
            "Masa choux",
            "Masa choux",
            "Manjar",
        ]

        # Cooking copies the group names; renaming them later does not touch the preparation.
        started = await ok(await client.post("/v1/preparations", json={"recipe_id": original["id"]}, headers=author), 201)
        assert [i["section"] for i in started["ingredients"]] == ["Masa choux", "Masa choux", "Manjar"]
        assert [s["section"] for s in started["steps"]] == ["Masa choux", "Manjar"]
        await ok(await client.put(f"/v1/recipes/{original['id']}/steps", json={"steps": [{"instructions": "Otro"}]}, headers=author))
        again = await ok(await client.get(f"/v1/preparations/{started['id']}", headers=author))
        assert [s["section"] for s in again["steps"]] == ["Masa choux", "Manjar"]


class TestPersonalizationAndPortfolio:

    async def test_personalize_save_and_portfolio(self, client, catalog):
        author = await sign_up(client, "chef@example.com")
        fan = await sign_up(client, "fan@example.com")
        original = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=author), 201)
        other = await ok(await client.post("/v1/recipes", json=recipe_body(catalog, "Galletas"), headers=author), 201)

        copy = await ok(
            await client.post(f"/v1/recipes/{original['id']}/personalizations", json={"title": "Mis brownies"}, headers=fan), 201
        )
        assert (copy["is_public"], copy["source_recipe_title"]) == (False, "Brownies")
        assert (await client.patch(f"/v1/recipes/{copy['id']}", json={"is_public": True}, headers=fan)).status_code == 400

        await ok(await client.put(f"/v1/portfolio/favorites/{other['id']}", headers=fan))
        await ok(await client.put(f"/v1/portfolio/favorites/{other['id']}", headers=fan))  # idempotent
        own = await client.put(f"/v1/portfolio/favorites/{copy['id']}", headers=fan)
        assert own.status_code == 400

        summary = await ok(await client.get("/v1/portfolio/summary", headers=fan))
        assert (summary["personalized_count"], summary["saved_count"], summary["total"]) == (1, 1, 2)

        # The author edits the original: the personalization learns about it, but does not change.
        await ok(await client.patch(f"/v1/recipes/{original['id']}", json={"servings": 20}, headers=author))
        detail = await ok(await client.get(f"/v1/recipes/{copy['id']}", headers=fan))
        assert detail["source_updated_since_personalized"] is True
        assert detail["servings"] != 20

        # The author hides the favorite: it leaves the fan's portfolio.
        await ok(await client.patch(f"/v1/recipes/{other['id']}", json={"is_public": False}, headers=author))
        favorites = await ok(await client.get("/v1/portfolio/favorites", headers=fan))
        assert favorites["total"] == 0


class TestRecommendations:

    async def test_deck_ranking_and_swipes(self, client, catalog):
        author = await sign_up(client, "baker@example.com")
        me = await sign_up(client, "hungry@example.com")
        units, mold, mixer = catalog["units"], catalog["equipment"][0], catalog["equipment"][1]

        def line(ingredient):
            return {"ingredient_id": catalog[ingredient], "quantity": "1", "unit_id": units["cup"]}

        async def publish(title, ingredients, equipment, headers=author, **extra):
            body = recipe_body(catalog, title, [line(i) for i in ingredients], equipment, **extra)
            return (await ok(await client.post("/v1/recipes", json=body, headers=headers), 201))["id"]

        all_mine = await publish("Todo tengo", ["flour", "butter"], [mold])  # 0.8*1 + 0.2*1 = 1.0
        no_mixer = await publish("Falta batidora", ["flour", "butter"], [mixer])  # 0.8*1 + 0.2*0 = 0.8
        half = await publish("La mitad", ["flour", "egg_white"], [])  # 0.8*0.5 + 0.2*1 = 0.6
        await publish("Nada que ver", ["egg_white"], [])  # no shared ingredient: not a candidate
        await publish("Privada", ["flour"], [], is_public=False)  # someone else's private recipe
        await ok(await client.put("/v1/equipment/mine", json={"equipment_id": mold}, headers=me))

        session = await ok(
            await client.post(
                "/v1/recommendations/sessions", json={"ingredient_ids": [catalog["flour"], catalog["butter"]]}, headers=me
            ),
            201,
        )
        deck = await ok(await client.get(f"/v1/recommendations/sessions/{session['id']}/deck", headers=me))

        assert [card["recipe_id"] for card in deck["items"]] == [all_mine, no_mixer, half]
        assert [card["rank_score"] for card in deck["items"]] == [1.0, 0.8, 0.6]
        assert deck["total"] == 3
        assert deck["items"][1]["has_all_equipment"] is False

        second_page = await ok(
            await client.get(f"/v1/recommendations/sessions/{session['id']}/deck", params={"limit": 2, "offset": 2}, headers=me)
        )
        assert ([c["recipe_id"] for c in second_page["items"]], second_page["total"]) == ([half], 3)
        past_end = await ok(
            await client.get(f"/v1/recommendations/sessions/{session['id']}/deck", params={"offset": 10}, headers=me)
        )
        assert (past_end["items"], past_end["total"]) == ([], 3)

        swipe = await ok(
            await client.post(
                f"/v1/recommendations/sessions/{session['id']}/swipes", json={"recipe_id": all_mine, "action": "saved"}, headers=me
            ),
            201,
        )
        assert swipe["action"] == "saved"
        deck = await ok(await client.get(f"/v1/recommendations/sessions/{session['id']}/deck", headers=me))
        assert all_mine not in [card["recipe_id"] for card in deck["items"]]
        status = await ok(await client.get("/v1/portfolio/favorites/status", params={"recipe_ids": all_mine}, headers=me))
        assert status[0]["is_saved"] is True

    async def test_personalization_replaces_original_in_deck(self, client, catalog):
        author = await sign_up(client, "orig@example.com")
        me = await sign_up(client, "variant@example.com")
        original = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=author), 201)
        mine = await ok(await client.post(f"/v1/recipes/{original['id']}/personalizations", json={}, headers=me), 201)

        session = await ok(
            await client.post("/v1/recommendations/sessions", json={"ingredient_ids": [catalog["flour"]]}, headers=me), 201
        )
        deck = await ok(await client.get(f"/v1/recommendations/sessions/{session['id']}/deck", headers=me))

        assert [(c["recipe_id"], c["is_own"]) for c in deck["items"]] == [(mine["id"], True)]


class TestPreparation:

    async def test_cook_a_recipe(self, client, catalog):
        headers = await sign_up(client, "cooking@example.com")
        recipe = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=headers), 201)

        started = await ok(await client.post("/v1/preparations", json={"recipe_id": recipe["id"]}, params={"unit_system": "metric"}, headers=headers), 201)
        prep_id = started["id"]
        flour = next(i for i in started["ingredients"] if i["original_unit_abbreviation"] == "cup")
        assert (Decimal(str(flour["quantity"])), flour["unit_abbreviation"]) == (Decimal("250"), "g")

        resumed = await client.post("/v1/preparations", json={"recipe_id": recipe["id"]}, headers=headers)
        assert (resumed.status_code, resumed.json()["id"]) == (200, prep_id)

        # The author edits the recipe mid-cooking: the preparation keeps its own copy.
        await ok(await client.put(f"/v1/recipes/{recipe['id']}/steps", json={"steps": [{"instructions": "Otro"}]}, headers=headers))

        detail = await ok(await client.post(f"/v1/preparations/{prep_id}/steps/1/complete", headers=headers))
        assert (detail["current_step_number"], detail["total_steps"]) == (2, 3)

        # The recipe detail converts the same way, keeping what the author wrote next to it.
        shown = await ok(await client.get(f"/v1/recipes/{recipe['id']}", params={"unit_system": "metric"}, headers=headers))
        flour_line = next(i for i in shown["ingredients"] if i["unit_abbreviation"] == "cup")
        assert (Decimal(str(flour_line["display_quantity"])), flour_line["display_unit_abbreviation"]) == (Decimal("250"), "g")
        assert (shown["unit_system"], flour_line["converted"]) == ("metric", True)
        as_written = await ok(await client.get(f"/v1/recipes/{recipe['id']}", params={"unit_system": "original"}, headers=headers))
        assert next(i for i in as_written["ingredients"] if i["id"] == flour_line["id"])["converted"] is False
        detail = await ok(await client.post(f"/v1/preparations/{prep_id}/steps/2/timer", headers=headers))
        assert 0 < detail["steps"][1]["timer_remaining_seconds"] <= 1800
        assert (await client.post(f"/v1/preparations/{prep_id}/steps/1/timer", headers=headers)).status_code == 400

        await ok(await client.post(f"/v1/preparations/{prep_id}/finish", headers=headers))
        assert (await client.post(f"/v1/preparations/{prep_id}/steps/3/complete", headers=headers)).status_code == 409

        history = await ok(await client.get("/v1/preparations", params={"status": "completed"}, headers=headers))
        assert [(p["id"], p["completed_steps"]) for p in history["items"]] == [(prep_id, 1)]

    async def test_preparation_is_private(self, client, catalog):
        owner = await sign_up(client, "prep-owner@example.com")
        other = await sign_up(client, "prep-other@example.com")
        recipe = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=owner), 201)
        prep = await ok(await client.post("/v1/preparations", json={"recipe_id": recipe["id"]}, headers=owner), 201)

        assert (await client.get(f"/v1/preparations/{prep['id']}", headers=other)).status_code == 404


class TestLocalizedIngredients:
    """Catalog names follow the viewer's preferred language; the domain keeps every language."""

    async def speaker(self, client, email, language):
        headers = await sign_up(client, email)
        await ok(await client.patch("/v1/users/me/language", json={"preferred_language": language}, headers=headers))
        return headers

    async def test_search_and_names_follow_the_viewer(self, client, catalog):
        english = await self.speaker(client, "en-search@example.com", "en")
        spanish = await self.speaker(client, "es-search@example.com", "es")

        for query, headers, expected in [
            ("flour", english, "All-purpose flour"),
            ("harina todo", english, "All-purpose flour"),  # any language matches
            ("all-purpose", spanish, "Harina todo uso (0000)"),
        ]:
            page = await ok(await client.get("/v1/ingredients", params={"q": query}, headers=headers))
            assert expected in [item["name"] for item in page["items"] if item["id"] == catalog["flour"]], query

    async def test_created_names_fall_back_and_stay_unique_across_languages(self, client, catalog):
        english = await self.speaker(client, "en-create@example.com", "en")
        spanish = await self.speaker(client, "es-create@example.com", "es")

        created = await ok(await client.post("/v1/ingredients", json={"name": "Cardamom pods"}, headers=english), 201)
        seen = await ok(await client.get(f"/v1/ingredients/{created['id']}", headers=spanish))
        assert seen["name"] == "Cardamom pods"  # untranslated: shown as written

        for name in ("butter", "MANTECA", "mantequilla", "Mantequilla / manteca", "Cardamom Pods"):
            response = await client.post("/v1/ingredients", json={"name": name}, headers=spanish)
            assert response.status_code == 409, name

    async def test_reviewed_translations_are_stored_and_guard_uniqueness(self, client, catalog):
        spanish = await self.speaker(client, "es-reviewed@example.com", "es")
        english = await self.speaker(client, "en-reviewed@example.com", "en")

        created = await ok(
            await client.post("/v1/ingredients", json={"name": "Pistacho", "translations": {"en": "Pistachio"}}, headers=spanish), 201
        )
        assert created["name"] == "Pistacho"
        seen = await ok(await client.get(f"/v1/ingredients/{created['id']}", headers=english))
        assert seen["name"] == "Pistachio"  # translated, not "shown as written"

        # The translation counts against uniqueness, in either language.
        clash = await client.post("/v1/ingredients", json={"name": "Nuevo", "translations": {"en": "pistachio"}}, headers=spanish)
        assert clash.status_code == 409
        # An unsupported language is a validation error, not a stored junk key.
        bad = await client.post("/v1/ingredients", json={"name": "Otro", "translations": {"fr": "Pistache"}}, headers=spanish)
        assert bad.status_code == 422

        equipment = await ok(
            await client.post(
                "/v1/equipment",
                json={"name": "Rodillo de repostería", "equipment_type": "utensil", "translations": {"en": "Pastry rolling pin"}},
                headers=spanish,
            ),
            201,
        )
        assert (await ok(await client.get(f"/v1/equipment/{equipment['id']}", headers=english)))["name"] == "Pastry rolling pin"

    async def test_search_ignores_accents_and_case(self, client, catalog):
        headers = await self.speaker(client, "accents@example.com", "es")

        async def names(path, q):
            page = await ok(await client.get(path, params={"q": q}, headers=headers))
            return [item.get("name") or item["title"] for item in page["items"]]

        # Typed without accent / in capitals / half a word: the accented name is still found.
        for q in ("azucar", "AZUCAR", "azúcar", "Azúc"):
            assert "Azúcar blanca" in await names("/v1/ingredients", q), q
        assert "Huevo" in await names("/v1/ingredients", "HUEVO")

        # The same for equipment and for recipes (title and description).
        await ok(await client.post("/v1/equipment", json={"name": "Rodillo de repostería", "equipment_type": "utensil"}, headers=headers), 201)
        assert "Rodillo de repostería" in await names("/v1/equipment", "reposteria")
        await ok(
            await client.post("/v1/recipes", json=recipe_body(catalog, "Tarta de limón", description="Con ralladura de limón"), headers=headers),
            201,
        )
        assert "Tarta de limón" in await names("/v1/recipes", "LIMON")
        assert await names("/v1/recipes", "lima") == []  # folding does not make unrelated words match

        # A typed '%' is a plain character, not a wildcard that matches everything.
        assert await names("/v1/ingredients", "100%") == []

    async def test_a_name_without_accents_is_the_same_name(self, client, catalog):
        headers = await self.speaker(client, "same-name@example.com", "es")

        response = await client.post("/v1/ingredients", json={"name": "Azucar blanca"}, headers=headers)

        assert response.status_code == 409  # "Azúcar blanca" already exists

    async def test_recipe_pantry_and_cooking_follow_the_viewer(self, client, catalog):
        author = await self.speaker(client, "es-author@example.com", "es")
        english = await self.speaker(client, "en-cook@example.com", "en")
        recipe = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=author), 201)

        names = lambda lines: {line.get("ingredient_name") for line in lines}
        detail = await ok(await client.get(f"/v1/recipes/{recipe['id']}", headers=english))
        assert {"All-purpose flour", "Butter"} <= names(detail["ingredients"])
        assert {"Harina todo uso (0000)", "Mantequilla / Manteca"} <= names((await ok(await client.get(f"/v1/recipes/{recipe['id']}", headers=author)))["ingredients"])

        await ok(await client.put("/v1/pantry", json={"ingredient_id": catalog["butter"]}, headers=english))
        assert [item["ingredient"]["name"] for item in await ok(await client.get("/v1/pantry", headers=english))] == ["Butter"]

        cooking = await ok(await client.post("/v1/preparations", json={"recipe_id": recipe["id"]}, headers=english), 201)
        assert {"All-purpose flour", "Butter"} <= names(cooking["ingredients"])
        # The snapshot keeps every language: switching language translates the history too.
        await ok(await client.patch("/v1/users/me/language", json={"preferred_language": "es"}, headers=english))
        again = await ok(await client.get(f"/v1/preparations/{cooking['id']}", headers=english))
        assert "Mantequilla / Manteca" in names(again["ingredients"])

    async def test_every_catalog_follows_the_viewer(self, client, catalog):
        english = await self.speaker(client, "en-catalogs@example.com", "en")
        spanish = await self.speaker(client, "es-catalogs@example.com", "es")

        async def names(path, headers, key="name"):
            body = await ok(await client.get(path, params={"limit": 100}, headers=headers))
            return {item[key] for item in (body["items"] if isinstance(body, dict) else body)}

        assert {"Oven", "Stand mixer"} <= await names("/v1/equipment", english)
        assert {"Horno", "Batidora planetaria"} <= await names("/v1/equipment", spanish)
        assert {"Cakes", "Cookies"} <= await names("/v1/recipe-categories", english)
        assert {"Easy", "Hard"} <= await names("/v1/difficulties", english)
        assert {"Christmas", "Gluten-free"} <= await names("/v1/recipe-tags", english)
        assert {"Flavor", "Diet"} <= await names("/v1/recipe-tags", english, key="group_name")
        assert {"cup", "gram"} <= await names("/v1/units", english)
        assert {"Flours & starches", "Dairy & eggs"} <= await names("/v1/categories", english, key="label")
        # The category code stays stable whatever the language: it is what clients filter by.
        assert "flour" in await names("/v1/categories", english)

        flour = await ok(await client.get(f"/v1/ingredients/{catalog['flour']}", headers=english))
        assert (flour["default_category"], flour["category_name"]) == ("flour", "Flours & starches")

        # Names that travel inside other modules' responses are translated too.
        recipe = await ok(await client.post("/v1/recipes", json=recipe_body(catalog), headers=spanish), 201)
        await ok(await client.put(f"/v1/portfolio/favorites/{recipe['id']}", headers=english))
        saved = await ok(await client.get("/v1/portfolio", params={"kind": "saved"}, headers=english))
        assert saved["items"][0]["difficulty_name"] in {"Easy", "Intermediate", "Hard"}

        session = await ok(
            await client.post("/v1/recommendations/sessions", json={"ingredient_ids": [catalog["flour"]]}, headers=english), 201
        )
        assert [i["name"] for i in session["ingredients"]] == ["All-purpose flour"]

    async def test_new_equipment_is_unique_across_languages(self, client, catalog):
        spanish = await self.speaker(client, "es-equipment@example.com", "es")
        for name in ("oven", "HORNO"):
            response = await client.post("/v1/equipment", json={"name": name, "equipment_type": "other"}, headers=spanish)
            assert response.status_code == 409, name
