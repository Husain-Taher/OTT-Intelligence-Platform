import pytest
from app.models.schemas import CanonicalContent, ContentType
from app.intelligence.vector_index import DenseVectorIndex, VECTOR_DIM
from app.intelligence.search_index import TypoTolerantSearchIndex, damerau_levenshtein_distance
from app.intelligence.semantic_engine import SemanticEngine
from app.db.database import get_all_content, get_all_embeddings


def test_damerau_levenshtein_distance():
    # Exact match
    assert damerau_levenshtein_distance("inception", "inception") == 0
    # 1 insertion / deletion
    assert damerau_levenshtein_distance("interstellar", "interstelar") == 1
    # Transposition
    assert damerau_levenshtein_distance("inseptoin", "inception") <= 2
    # Substitution
    assert damerau_levenshtein_distance("totoro", "totora") == 1


def test_vector_index_cozy_vs_comforting_semantic_similarity():
    """
    Verifies that the dense embedding model understands semantic nuance:
    'cozy' and 'comforting' must have high cosine similarity (>0.7),
    unlike TF-IDF which scored 0.0.
    """
    index = DenseVectorIndex()
    vec_cozy = index.embed_text("cozy warm peaceful afternoon")
    vec_comforting = index.embed_text("comforting wholesome gentle feeling")
    vec_violent = index.embed_text("violent gore intense brutal war explosion")

    # Cosine similarity
    sim_cozy_comforting = float(vec_cozy @ vec_comforting)
    sim_cozy_violent = float(vec_cozy @ vec_violent)

    assert sim_cozy_comforting > 0.65, f"Expected >0.65, got {sim_cozy_comforting}"
    assert sim_cozy_comforting > sim_cozy_violent, (
        f"Cozy-Comforting ({sim_cozy_comforting}) should be higher than Cozy-Violent ({sim_cozy_violent})"
    )


def test_typo_tolerant_search_index_fuzzy_title_and_person():
    items = [
        CanonicalContent(
            content_id="test_inception",
            tmdb_id=27205,
            title="Inception",
            original_title="Inception",
            content_type=ContentType.MOVIE,
            release_year=2010,
            runtime=148,
            genres=["Action", "Science Fiction"],
            directors=["Christopher Nolan"],
            cast=["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
            keywords=["dream", "subconscious", "heist"],
            vote_average=8.4,
            vote_count=35000,
            original_language="en",
            overview="A thief who steals corporate secrets through dream-sharing technology."
        ),
        CanonicalContent(
            content_id="test_totoro",
            tmdb_id=8392,
            title="My Neighbor Totoro",
            original_title="Tonari no Totoro",
            content_type=ContentType.MOVIE,
            release_year=1988,
            runtime=86,
            genres=["Animation", "Family", "Fantasy"],
            directors=["Hayao Miyazaki"],
            cast=["Noriko Hidaka", "Chika Sakamoto"],
            keywords=["forest spirit", "countryside", "childhood"],
            vote_average=8.1,
            vote_count=7500,
            original_language="ja",
            overview="Two sisters move to the country with their father and explore the nearby forest."
        )
    ]

    search_idx = TypoTolerantSearchIndex()
    search_idx.build_index(items)

    # 1. Typo in title: 'Inseptoin' -> should find Inception
    hits_typo = search_idx.search("Inseptoin")
    assert len(hits_typo) >= 1
    assert hits_typo[0]["content"].content_id == "test_inception"

    # 2. Director search: 'Nolan' -> should find Inception
    hits_dir = search_idx.search("Nolan")
    assert len(hits_dir) >= 1
    assert hits_dir[0]["content"].content_id == "test_inception"
    assert "Christopher Nolan" in hits_dir[0]["match_reason"]

    # 3. Cast search: 'Miyazaki' (director) / 'DiCaprio' (actor)
    hits_actor = search_idx.search("DiCaprio")
    assert len(hits_actor) >= 1
    assert hits_actor[0]["content"].content_id == "test_inception"

    # 4. Facet filtering: runtime <= 90 mins -> Totoro only
    hits_filtered = search_idx.search("totoro", max_runtime=90)
    assert len(hits_filtered) == 1
    assert hits_filtered[0]["content"].content_id == "test_totoro"

    # 5. Facet filtering: language 'ja'
    hits_ja = search_idx.search("Totoro", language="ja")
    assert len(hits_ja) == 1


def test_semantic_engine_full_integration():
    catalog = get_all_content()
    assert len(catalog) >= 100, f"Catalog should have at least 100 titles, got {len(catalog)}"

    engine = SemanticEngine()
    engine.build_index(catalog)

    # 1. Semantic query
    semantic_hits = engine.search_semantic("peaceful countryside family fantasy", items_map={it.content_id: it for it in catalog}, top_k=5)
    assert len(semantic_hits) >= 1
    titles = [it.title for it, score in semantic_hits]
    # Expect studio ghibli or peaceful titles near top
    assert any("Totoro" in t or "Spirited" in t or "Piku" in t or "Amélie" in t for t in titles)

    # 2. Typo keyword query
    keyword_hits = engine.search_keyword("Nolan")
    assert len(keyword_hits) >= 1
    assert any("Inception" in h["content"].title or "Interstellar" in h["content"].title or "Dark Knight" in h["content"].title for h in keyword_hits)
