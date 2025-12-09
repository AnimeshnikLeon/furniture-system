import decimal
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
import time

DB_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST','localhost')}:{os.getenv('POSTGRES_PORT','5432')}"
    f"/{os.getenv('POSTGRES_DB')}"
)

ROOT = Path(__file__).resolve().parent
DATA = Path("/app/data") if Path("/app/data").exists() else ROOT.parent / "data"

engine = create_engine(DB_URL, echo=False, future=True)


def read_xlsx(path, **kwargs):
    return pd.read_excel(path, dtype=str, engine="openpyxl", **kwargs)


def to_decimal_ru(value: str) -> decimal.Decimal:
    value = str(value).strip().replace("%", "").replace(" ", "")
    if not value:
        return None
    value = value.replace(",", ".")
    return decimal.Decimal(value)


def import_product_types(conn):
    df = read_xlsx(DATA / "Product_type_import.xlsx")
    df.rename(columns={
        "Тип продукции": "name",
        "Коэффициент типа продукции": "coefficient"
    }, inplace=True)

    for _, row in df.iterrows():
        coeff = to_decimal_ru(row["coefficient"])
        conn.execute(
            text("""
                INSERT INTO product_type (name, coefficient)
                VALUES (:name, :coefficient)
                ON CONFLICT (name) DO UPDATE
                SET coefficient = EXCLUDED.coefficient
            """),
            {"name": row["name"].strip(),
             "coefficient": coeff}
        )


def import_material_types(conn):
    df = read_xlsx(DATA / "Material_type_import.xlsx")
    df.rename(columns={
        "Тип материала": "name",
        "Процент потерь сырья": "loss"
    }, inplace=True)

    for _, row in df.iterrows():
        loss = to_decimal_ru(row["loss"]) / decimal.Decimal("100")
        conn.execute(
            text("""
                INSERT INTO material_type (name, loss_percent)
                VALUES (:name, :loss)
                ON CONFLICT (name) DO UPDATE
                SET loss_percent = EXCLUDED.loss_percent
            """),
            {"name": row["name"].strip(),
             "loss": loss}
        )


def import_workshops(conn):
    df = read_xlsx(DATA / "Workshops_import.xlsx")

    df.columns = [str(c).strip() for c in df.columns]

    col_name = None
    col_type = None
    col_workers = None
    for c in df.columns:
        if "Название цеха" in c:
            col_name = c
        elif "Тип цеха" in c:
            col_type = c
        elif "Количество человек" in c:
            col_workers = c

    if not (col_name and col_type and col_workers):
        raise RuntimeError(
            f"Не удалось распознать столбцы в Workshops_import.xlsx. "
            f"Найдено: {df.columns.tolist()}"
        )

    df = df.rename(columns={
        col_name: "workshop_name",
        col_type: "workshop_type",
        col_workers: "workers"
    })

    for wt in sorted(df["workshop_type"].dropna().unique()):
        name = str(wt).strip()
        conn.execute(
            text("""
                INSERT INTO workshop_type (name)
                VALUES (:name)
                ON CONFLICT (name) DO NOTHING
            """),
            {"name": name}
        )

    for _, row in df.iterrows():
        wt_name = str(row["workshop_type"]).strip()
        ws_name = str(row["workshop_name"]).strip()
        workers_raw = str(row["workers"]).strip()
        workers = int(float(workers_raw.replace(",", ".")))

        wt_id = conn.execute(
            text("SELECT id FROM workshop_type WHERE name = :name"),
            {"name": wt_name}
        ).scalar_one()

        conn.execute(
            text("""
                INSERT INTO workshop (name, workshop_type_id, workers_required)
                VALUES (:name, :wt_id, :workers)
                ON CONFLICT (name) DO UPDATE
                SET workshop_type_id = EXCLUDED.workshop_type_id,
                    workers_required = EXCLUDED.workers_required
            """),
            {"name": ws_name, "wt_id": wt_id, "workers": workers}
        )



def import_products(conn):
    df = read_xlsx(DATA / "Products_import.xlsx")
    df.rename(columns={
        "Тип продукции": "product_type",
        "Наименование продукции": "name",
        "Артикул": "article",
        "Минимальная стоимость для партнера": "min_price",
        "Основной материал": "material_type"
    }, inplace=True)

    for _, row in df.iterrows():
        pt_name = row["product_type"].strip()
        mt_name = row["material_type"].strip()
        pt_id = conn.execute(
            text("SELECT id FROM product_type WHERE name = :n"),
            {"n": pt_name}
        ).scalar_one()
        mt_id = conn.execute(
            text("SELECT id FROM material_type WHERE name = :n"),
            {"n": mt_name}
        ).scalar_one()

        price = to_decimal_ru(row["min_price"])

        conn.execute(
            text("""
                INSERT INTO product
                    (name, article, product_type_id, material_type_id, min_partner_price)
                VALUES (:name, :article, :pt_id, :mt_id, :price)
                ON CONFLICT (article) DO UPDATE
                SET name = EXCLUDED.name,
                    product_type_id = EXCLUDED.product_type_id,
                    material_type_id = EXCLUDED.material_type_id,
                    min_partner_price = EXCLUDED.min_partner_price
            """),
            {
                "name": row["name"].strip(),
                "article": str(row["article"]).strip(),
                "pt_id": pt_id,
                "mt_id": mt_id,
                "price": price
            }
        )


def import_product_workshops(conn):
    df = read_xlsx(DATA / "Product_workshops_import.xlsx")
    df.rename(columns={
        "Наименование продукции": "product_name",
        "Название цеха": "workshop_name",
        "Время изготовления, ч": "time_hours"
    }, inplace=True)

    for _, row in df.iterrows():
        pname = row["product_name"].strip()
        wname = row["workshop_name"].strip()

        prod_id = conn.execute(
            text("SELECT id FROM product WHERE name = :n"),
            {"n": pname}
        ).scalar_one()
        ws_id = conn.execute(
            text("SELECT id FROM workshop WHERE name = :n"),
            {"n": wname}
        ).scalar_one()

        t = to_decimal_ru(row["time_hours"])

        conn.execute(
            text("""
                INSERT INTO product_workshop
                    (product_id, workshop_id, production_time_hours)
                VALUES (:pid, :wid, :t)
                ON CONFLICT (product_id, workshop_id) DO UPDATE
                SET production_time_hours = EXCLUDED.production_time_hours
            """),
            {"pid": prod_id, "wid": ws_id, "t": t}
        )


def main():
    print("Connecting to DB:", DB_URL)

    # ждём базу (на случай, если healthcheck чуть опоздает)
    for attempt in range(10):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except Exception as e:
            print(f"DB is not ready yet (attempt {attempt + 1}/10): {e}")
            time.sleep(3)
    else:
        raise RuntimeError("Database is still not ready after retries")

    with engine.begin() as conn:
        import_product_types(conn)
        import_material_types(conn)
        import_workshops(conn)
        import_products(conn)
        import_product_workshops(conn)

    print("Import finished.")



if __name__ == "__main__":
    main()
