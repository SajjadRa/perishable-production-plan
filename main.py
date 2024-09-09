import pandas as pd

from logger import logger
from model import OptimizationModel

"""
A company that produces dairy products would like to calculate a production plan for its main plant.
Their demand is expressed by product/plant at a daily bucket for a horizon of 5 weeks.
Because the capacity lines are really saturated, they can face shortage but they can’t stock too much in advance as the products have a short shelf live and expire within 12 days. 
The challenge they face today is reaching a good service level while reducing the waste (products are thrown away because they reached their expiry date). 

The main constraints they have are as follow:
The demand should be met at a daily level.
The capacity of the lines cannot be exceeded.
A minimum stock is defined for each product that should be met.
We would like to produce following a minimum order quantity (MOQ): We allow production only if it exceeds a certain MOQ that is defined by product x Production Line
The production should be a multiple of a given lot size: The lot size will be is defined by product x Production Line
Extra information:
The products can be produced on several lines, but each product has a preferred line
The demand is expressed by units, but the capacity of the lines is expressed in hours. Each product has a production rate related the production line that will help express the demand in hours. 
To avoid infeasibility, we will allow shortage and stock.


The candidate is required to formulate this problem as Linear Program in Integer Numbers. 

Please also prepare to argument the following questions:
What are the drivers of complexity?
What mathematical formulation can be considered as an alternative to Integer Linear programming? 

"""


def run():
    model = OptimizationModel()
    model.solve()

    production_amounts = model.read_production_amounts()
    production_plan = pd.DataFrame(
        [(*k, v) for k, v in production_amounts.items()],
        columns=["product", "plant_line", "day", "production_amount"],
    )
    production_plan_table = production_plan.pivot(
        index=["product", "plant_line"], columns="day"
    )["production_amount"].T

    stock = model.read_stock()
    stock = pd.DataFrame(
        [(*k, v) for k, v in stock.items()],
        columns=["product", "plant", "day", "stock"],
    )
    stock_table = stock.pivot(index=["product", "plant"], columns="day")["stock"].T

    sales = model.read_sales()
    sales = pd.DataFrame(
        [(*k, v) for k, v in sales.items()],
        columns=["product", "plant", "day", "shortage"],
    )
    sales_table = sales.pivot(index=["product", "plant"], columns="day")["shortage"].T

    shortage = model.read_shortage()
    shortage = pd.DataFrame(
        [(*k, v) for k, v in shortage.items()],
        columns=["product", "plant", "day", "shortage"],
    )
    shortage_table = shortage.pivot(index=["product", "plant"], columns="day")[
        "shortage"
    ].T

    logger("Done!")


# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    run()
