import api from './axios'

/**
 * Debounced food search against /api/foods/search/.
 * Falls back to OpenFoodFacts on the backend when local DB has no matches.
 */
export async function searchFoods(searchTerms) {
  const query = searchTerms.trim()
  if (query.length < 2) {
    return { results: [], source: null, count: 0 }
  }

  const { data } = await api.get('/foods/search/', {
    params: { search_terms: query },
  })

  return {
    results: data.results ?? [],
    source: data.source ?? null,
    count: data.count ?? 0,
  }
}
