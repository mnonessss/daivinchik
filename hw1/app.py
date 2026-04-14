from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import *
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)



def create_order(CustomerID, **kwargs):
    session = Session()
    try:
        customer = (
            session.query(Customers)
            .filter(Customers.customer_id == CustomerID)
            .first()
        )
        if customer is None:
            raise ValueError(f"Customer with ID = {CustomerID} wasn't found")

        if not kwargs:
            raise ValueError("Order must contain at least one product")

        order = Orders(customer_id=CustomerID, total_amount=0)
        session.add(order)
        session.flush()
        total_amount = 0
        for product_name, quantity in kwargs.items():
            if not isinstance(quantity, int):
                raise ValueError(f"Quantity for product {product_name} must be an integer")
            if quantity <= 0:
                raise ValueError(f"Quantity for product {product_name} must be positive")

            if not isinstance(product_name, str):
                raise ValueError("Product name must be string")
            
            product_obj = (
                session.query(Products)
                .filter(Products.product_name == product_name)
                .first()
            )
            if product_obj is None:
                raise ValueError(f"Product '{product_name}' was not found")

            subtotal = product_obj.price * quantity
            order_item = OrderItems(
                order_id=order.order_id,
                product_id=product_obj.product_id,
                quantity=quantity,
                subtotal=subtotal,
            )
            session.add(order_item)
            total_amount += subtotal

        order.total_amount = total_amount
        session.commit()
        session.refresh(order)
        return order
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


def change_email(CustomerID, new_email):
    session = Session()
    try:
        customer = session.query(Customers).filter(Customers.customer_id == CustomerID).first()
        if customer is None:
            raise ValueError(f"Customer with ID = {CustomerID} wasn't found")
        customer.email = new_email
        session.commit()
        return customer
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


def add_product(ProductName, Price):
    session = Session()
    try:
        product = Products(product_name=ProductName, price=Price)
        session.add(product)
        session.commit()
        return product
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    add_product("milk", 100)
    add_product("bread", 50)
    create_order(1, milk=2, bread=3)
    change_email(1, "new_email@gmail.com")