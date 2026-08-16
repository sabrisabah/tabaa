import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import FoodSearch from '../foods/FoodSearch'
import ServingQuantityModal from '../foods/ServingQuantityModal'

export default function AddFoodModal({ mealType, onClose, onSubmit }) {
  const { t } = useTranslation()
  const [selectedFood, setSelectedFood] = useState(null)
  const mealLabel = t(`meals.${mealType}`)

  function handleSelectFood(food) {
    setSelectedFood(food)
  }

  function handleBackToSearch() {
    setSelectedFood(null)
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center">
        <div
          className="w-full max-w-lg rounded-2xl bg-white shadow-xl"
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-food-title"
        >
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <h2 id="add-food-title" className="text-lg font-semibold text-slate-900">
                {t('food.addTitle')}
              </h2>
              <p className="text-sm text-slate-500">{mealLabel}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
            >
              {t('food.close')}
            </button>
          </div>

          <div className="px-5 py-4">
            <FoodSearch onSelectFood={handleSelectFood} />
          </div>
        </div>
      </div>

      {selectedFood ? (
        <ServingQuantityModal
          food={selectedFood}
          mealType={mealType}
          onBack={handleBackToSearch}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </>
  )
}
