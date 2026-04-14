"""Changed names for columns in database

Revision ID: 3f2e00b3b24a
Revises: 9a01c3978523
Create Date: 2026-04-14 18:39:58.775623

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3f2e00b3b24a'
down_revision: Union[str, Sequence[str], None] = '9a01c3978523'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop FKs first, then rename columns, then recreate FKs.
    op.drop_constraint(op.f("order_items_OrderID_fkey"), "order_items", type_="foreignkey")
    op.drop_constraint(op.f("order_items_ProductID_fkey"), "order_items", type_="foreignkey")
    op.drop_constraint(op.f("orders_CustomerID_fkey"), "orders", type_="foreignkey")

    op.alter_column("customers", "CustomerID", new_column_name="customer_id")
    op.alter_column("customers", "FirstName", new_column_name="first_name")
    op.alter_column("customers", "LastName", new_column_name="last_name")
    op.alter_column("customers", "Email", new_column_name="email")

    op.alter_column("orders", "OrderID", new_column_name="order_id")
    op.alter_column("orders", "CustomerID", new_column_name="customer_id")
    op.alter_column("orders", "OrderDate", new_column_name="order_date")
    op.alter_column("orders", "TotalAmount", new_column_name="total_amount")

    op.alter_column("order_items", "OrderItemID", new_column_name="order_item_id")
    op.alter_column("order_items", "OrderID", new_column_name="order_id")
    op.alter_column("order_items", "ProductID", new_column_name="product_id")
    op.alter_column("order_items", "Quantity", new_column_name="quantity")
    op.alter_column("order_items", "Subtotal", new_column_name="subtotal")

    op.alter_column("products", "ProductID", new_column_name="product_id")
    op.alter_column("products", "ProductName", new_column_name="product_name")
    op.alter_column("products", "Price", new_column_name="price")

    op.drop_index(op.f("ix_customers_CustomerID"), table_name="customers")
    op.drop_index(op.f("ix_orders_OrderID"), table_name="orders")
    op.drop_index(op.f("ix_order_items_OrderItemID"), table_name="order_items")
    op.drop_index(op.f("ix_products_ProductID"), table_name="products")
    op.drop_constraint(op.f("products_ProductName_key"), "products", type_="unique")

    op.create_index(op.f("ix_customers_customer_id"), "customers", ["customer_id"], unique=False)
    op.create_index(op.f("ix_orders_order_id"), "orders", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_order_item_id"), "order_items", ["order_item_id"], unique=False)
    op.create_index(op.f("ix_products_product_id"), "products", ["product_id"], unique=False)
    op.create_unique_constraint(op.f("products_product_name_key"), "products", ["product_name"])

    op.create_foreign_key(
        op.f("orders_customer_id_fkey"),
        "orders",
        "customers",
        ["customer_id"],
        ["customer_id"],
    )
    op.create_foreign_key(
        op.f("order_items_order_id_fkey"),
        "order_items",
        "orders",
        ["order_id"],
        ["order_id"],
    )
    op.create_foreign_key(
        op.f("order_items_product_id_fkey"),
        "order_items",
        "products",
        ["product_id"],
        ["product_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("order_items_order_id_fkey"), "order_items", type_="foreignkey")
    op.drop_constraint(op.f("order_items_product_id_fkey"), "order_items", type_="foreignkey")
    op.drop_constraint(op.f("orders_customer_id_fkey"), "orders", type_="foreignkey")

    op.drop_index(op.f("ix_customers_customer_id"), table_name="customers")
    op.drop_index(op.f("ix_orders_order_id"), table_name="orders")
    op.drop_index(op.f("ix_order_items_order_item_id"), table_name="order_items")
    op.drop_index(op.f("ix_products_product_id"), table_name="products")
    op.drop_constraint(op.f("products_product_name_key"), "products", type_="unique")

    op.alter_column("customers", "customer_id", new_column_name="CustomerID")
    op.alter_column("customers", "first_name", new_column_name="FirstName")
    op.alter_column("customers", "last_name", new_column_name="LastName")
    op.alter_column("customers", "email", new_column_name="Email")

    op.alter_column("orders", "order_id", new_column_name="OrderID")
    op.alter_column("orders", "customer_id", new_column_name="CustomerID")
    op.alter_column("orders", "order_date", new_column_name="OrderDate")
    op.alter_column("orders", "total_amount", new_column_name="TotalAmount")

    op.alter_column("order_items", "order_item_id", new_column_name="OrderItemID")
    op.alter_column("order_items", "order_id", new_column_name="OrderID")
    op.alter_column("order_items", "product_id", new_column_name="ProductID")
    op.alter_column("order_items", "quantity", new_column_name="Quantity")
    op.alter_column("order_items", "subtotal", new_column_name="Subtotal")

    op.alter_column("products", "product_id", new_column_name="ProductID")
    op.alter_column("products", "product_name", new_column_name="ProductName")
    op.alter_column("products", "price", new_column_name="Price")

    op.create_index(op.f("ix_customers_CustomerID"), "customers", ["CustomerID"], unique=False)
    op.create_index(op.f("ix_orders_OrderID"), "orders", ["OrderID"], unique=False)
    op.create_index(op.f("ix_order_items_OrderItemID"), "order_items", ["OrderItemID"], unique=False)
    op.create_index(op.f("ix_products_ProductID"), "products", ["ProductID"], unique=False)
    op.create_unique_constraint(op.f("products_ProductName_key"), "products", ["ProductName"])

    op.create_foreign_key(
        op.f("orders_CustomerID_fkey"),
        "orders",
        "customers",
        ["CustomerID"],
        ["CustomerID"],
    )
    op.create_foreign_key(
        op.f("order_items_OrderID_fkey"),
        "order_items",
        "orders",
        ["OrderID"],
        ["OrderID"],
    )
    op.create_foreign_key(
        op.f("order_items_ProductID_fkey"),
        "order_items",
        "products",
        ["ProductID"],
        ["ProductID"],
    )
