from decimal import Decimal, InvalidOperation, ROUND_CEILING
from sqlalchemy.orm import Session

from . import models


def calculate_raw_material_amount(
    db: Session,
    product_type_id: int,
    material_type_id: int,
    quantity: int,
    param1: float,
    param2: float,
) -> int:
    """
    Рассчитывает целое количество сырья для производства заданного количества продукции.

    Алгоритм:
    1. По идентификаторам типов продукции и материала считываются:
       - коэффициент типа продукции (product_type.coefficient),
       - процент потерь сырья (material_type.loss_percent, хранится как доля: 0.05 = 5%).
    2. Количество сырья на одну единицу продукции:
           per_unit = param1 * param2 * coefficient
    3. Для заданного количества продукции:
           total_without_losses = per_unit * quantity
    4. Учитываем потери сырья:
           total_with_losses = total_without_losses * (1 + loss_percent)
    5. Результат округляется вверх до целого (ceil) и возвращается как int.

    Валидация:
    - quantity — целое число > 0;
    - param1, param2 — положительные вещественные числа;
    - product_type и material_type с указанными id должны существовать;
    - при любой ошибке или неподходящих данных возвращается -1.
    """
    # Проверка количества продукции
    try:
        qty = int(quantity)
    except (TypeError, ValueError):
        return -1
    if qty <= 0:
        return -1

    # Проверка параметров продукции как положительных вещественных чисел
    try:
        p1 = Decimal(str(param1))
        p2 = Decimal(str(param2))
    except (InvalidOperation, TypeError, ValueError):
        return -1
    if p1 <= 0 or p2 <= 0:
        return -1

    # Загрузка справочников
    product_type = db.get(models.ProductType, product_type_id)
    material_type = db.get(models.MaterialType, material_type_id)
    if not product_type or not material_type:
        return -1

    coeff = product_type.coefficient
    loss = material_type.loss_percent

    if coeff is None or loss is None:
        return -1

    coeff = Decimal(coeff)
    loss = Decimal(loss)

    if coeff <= 0 or loss < 0:
        return -1

    # Расчёт количества сырья на единицу продукции
    per_unit = p1 * p2 * coeff
    if per_unit <= 0:
        return -1

    # Общее количество без учёта потерь
    total_without_losses = per_unit * qty

    # Учитываем процент потерь сырья (loss хранится как доля, например 0.05)
    total_with_losses = total_without_losses * (Decimal("1") + loss)

    if total_with_losses <= 0:
        return -1

    # Округление вверх до целого количества единиц сырья
    return int(total_with_losses.to_integral_value(rounding=ROUND_CEILING))
