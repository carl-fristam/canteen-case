from data.product_store import ProductStore
from summarize import summarize_plan
from llm.fake_planner import fake_plan_week

def test_summarize_calculation():
    store = ProductStore()
    candidates = store.candidates()
    plan = fake_plan_week(candidates)
    
    summary = summarize_plan(plan, store)
    
    # Grand total should be the sum of both tracks
    assert summary.grand_total_cost_eur == summary.meat_track.total_cost_eur + summary.vegetarian_track.total_cost_eur
    
    # Check that we have some data
    assert summary.meat_track.total_calories_kcal > 0
    assert summary.vegetarian_track.total_cost_eur > 0
    
    # Check allergens (fake_planner uses first few products, might have none)
    assert isinstance(summary.meat_track.allergens, list)
