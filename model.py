import sys
import time
from random import randint
from typing import Dict, Tuple, NewType

from ortools.linear_solver import pywraplp

from base import Plant, Product, PlantLine
from logger import logger


INFEASIBLE = pywraplp.Solver.INFEASIBLE
FEASIBLE = pywraplp.Solver.FEASIBLE
OPTIMAL = pywraplp.Solver.OPTIMAL

RUN_TIME = 120  # seconds

Day = NewType("Day", int)

NUM_PLANTS = 1
NUM_PRODUCTS = 2
LINES_PER_PLANT = 2
HORIZON = [Day(i + 1) for i in range(5 * 7)]
PLANTS = [Plant(i, LINES_PER_PLANT) for i in range(NUM_PLANTS)]
PLANT_LINES = [line for p in PLANTS for line in p.lines]
PRODUCTS = [Product(i) for i in range(NUM_PRODUCTS)]
DEMANDS = {
    (pr, pl, d): randint(150, 200) for pr in PRODUCTS for pl in PLANTS for d in HORIZON
}
PRODUCTION_RATES = {
    (pr, pl): randint(8, 10) for pr in PRODUCTS for pl in PLANT_LINES
}  # per hour
MIN_STOCK = {(pr, pl): 5 for pr in PRODUCTS for pl in PLANTS}
MOQ = {(pr, pl): 50 for pr in PRODUCTS for pl in PLANT_LINES}
LOT_SIZE = {(pr, pl): 5 for pr in PRODUCTS for pl in PLANT_LINES}
LINE_CAPACITY = {(pl, d): 24 for pl in PLANT_LINES for d in HORIZON}
SHORTAGE_PENALTY = {pr: 200 for pr in PRODUCTS}
LOW_STOCK_PENALTY = {pr: 50 for pr in PRODUCTS}
PRODUCT_AGE = {pr: 12 for pr in PRODUCTS}
PRODUCTION_COST = {(pr, pl): randint(5, 20) for pr in PRODUCTS for pl in PLANT_LINES}

TOTAL_DEMAND = {
    (pr, pl): sum(DEMANDS[pr, pl, d] for d in HORIZON)
    for pr in PRODUCTS
    for pl in PLANTS
}


class OptimizationModel:
    math_model: pywraplp.Solver
    solver: pywraplp.Solver
    production_amount: Dict[Tuple[Product, PlantLine, Day], pywraplp.Solver.IntVar]
    is_produced: Dict[Tuple[Product, PlantLine, Day], pywraplp.Solver.BoolVar]
    number_of_lots: Dict[Tuple[Product, PlantLine, Day], pywraplp.Solver.IntVar]
    stock_by_age: Dict[Tuple[Product, Plant, Day, int], pywraplp.Solver.IntVar]
    sales_by_age: Dict[Tuple[Product, Plant, Day, int], pywraplp.Solver.IntVar]
    shortage: Dict[Tuple[Product, Plant, Day], pywraplp.Solver.IntVar]
    short_on_stock: Dict[Tuple[Product, Plant, Day], pywraplp.Solver.IntVar]
    status: str
    solution_time: float

    def __init__(self):
        logger.info(">> Creating Optimization Model..")
        self.math_model = pywraplp.Solver.CreateSolver("CBC")
        self.solver = self.math_model
        self.create_variables()
        self.add_constraints()
        self.set_objective_function()

    def int_variable(self, lb: int, ub: int, name: str):
        return self.math_model.IntVar(lb, ub, name)

    def bool_variable(self, name: str):
        return self.math_model.BoolVar(name)

    def create_variables(self):
        logger.info("Creating variables..")
        self.production_amount = {
            (pr, line, d): self.int_variable(
                lb=0,
                ub=TOTAL_DEMAND[pr, line.plant],
                name=f"production_amount_{pr}_{line}_{d}",
            )
            for pr in PRODUCTS
            for line in PLANT_LINES
            for d in HORIZON
        }
        self.is_produced = {
            (pr, line, d): self.bool_variable(name=f"is_produced_{pr}_{line}_{d}")
            for pr in PRODUCTS
            for line in PLANT_LINES
            for d in HORIZON
        }
        self.number_of_lots = {
            (pr, line, d): self.int_variable(
                lb=0,
                ub=TOTAL_DEMAND[pr, line.plant] // LOT_SIZE[pr, line] + 1,
                name=f"number_of_lots_{pr}_{line}_{d}",
            )
            for pr in PRODUCTS
            for line in PLANT_LINES
            for d in HORIZON
        }
        self.stock_by_age = {
            (pr, pl, d, age): self.int_variable(
                lb=0, ub=TOTAL_DEMAND[pr, pl], name=f"stock_{pr}_{pl}_{d}_{age}"
            )
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
            for age in range(min(d, PRODUCT_AGE[pr]))
        }
        self.sales_by_age = {
            (pr, pl, d, age): self.int_variable(
                lb=0, ub=TOTAL_DEMAND[pr, pl], name=f"sales_{pr}_{pl}_{d}_{age}"
            )
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
            for age in range(min(d, PRODUCT_AGE[pr]))
        }

        self.shortage = {
            (pr, pl, d): self.int_variable(
                lb=0, ub=TOTAL_DEMAND[pr, pl], name=f"shortage_{pr}_{pl}_{d}"
            )
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        }

        self.short_on_stock = {
            (pr, pl, d): self.int_variable(
                lb=0, ub=TOTAL_DEMAND[pr, pl], name=f"short_on_stock_{pr}_{pl}_{d}"
            )
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        }

    def add_constraints(self):
        # positive production amount if is_produced is True and at least MOQ, and multiple of LOT_SIZE
        for pr, line, d in self.production_amount:
            self.math_model.Add(
                self.production_amount[pr, line, d]
                <= TOTAL_DEMAND[pr, line.plant] * self.is_produced[pr, line, d]
            )
            self.math_model.Add(
                self.production_amount[pr, line, d]
                >= MOQ[pr, line] * self.is_produced[pr, line, d]
            )
            self.math_model.Add(
                self.production_amount[pr, line, d]
                == LOT_SIZE[pr, line] * self.number_of_lots[pr, line, d]
            )
        # line capacity constraint
        for line, d in LINE_CAPACITY:
            self.math_model.Add(
                sum(
                    self.production_amount[pr, line, d] / PRODUCTION_RATES[pr, line]
                    for pr in PRODUCTS
                )
                <= LINE_CAPACITY[line, d]
            )

        # demand + shortage constraint
        for pr, pl, d in DEMANDS:
            # sales constraint
            # we assume shortage is lost sales (no backorder)
            self.math_model.Add(
                sum(
                    self.sales_by_age[pr, pl, d, age]
                    for age in range(min(d, PRODUCT_AGE[pr]))
                )
                + self.shortage[pr, pl, d]
                == DEMANDS[pr, pl, d]
            )

            # stock constraint, considering the age of the product
            for age in range(min(d, PRODUCT_AGE[pr])):
                if age == 0:
                    self.math_model.Add(
                        self.stock_by_age[pr, pl, d, age]
                        == sum(self.production_amount[pr, line, d] for line in pl.lines)
                        - self.sales_by_age[pr, pl, d, age]
                    )
                else:
                    self.math_model.Add(
                        self.stock_by_age[pr, pl, d, age]
                        == self.stock_by_age[pr, pl, Day(d - 1), age - 1]
                        - self.sales_by_age[pr, pl, d, age]
                    )

            # minimum stock constraint
            self.math_model.Add(
                sum(
                    self.stock_by_age[pr, pl, d, age]
                    for age in range(min(d, PRODUCT_AGE[pr]))
                )
                + self.short_on_stock[pr, pl, d]
                >= MIN_STOCK[pr, pl]
            )

    def set_objective_function(self):
        # shortage penalty
        shortage_penalty = sum(
            SHORTAGE_PENALTY[pr] * self.shortage[pr, pl, d]
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        )
        # production cost: to incorporate the preferred line per product
        #   + minimise the waste (products are thrown away because they reached their expiry date) and unnecessary stock
        production_cost = sum(
            PRODUCTION_COST[pr, line] * self.production_amount[pr, line, d]
            for pr in PRODUCTS
            for line in PLANT_LINES
            for d in HORIZON
        )

        # short on stock penalty
        short_on_stock_penalty = sum(
            LOW_STOCK_PENALTY[pr] * self.short_on_stock[pr, pl, d]
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        )
        self.math_model.Minimize(
            shortage_penalty + production_cost + short_on_stock_penalty
        )

    def solve(self):
        logger.info(
            f">> Solving Optimization Model.. (can take up to {RUN_TIME} seconds)"
        )
        start_time = time.time()
        self.set_runtime()
        self.status = self.math_model.Solve()
        self.solution_time = round(time.time() - start_time, 1)
        if self.status == INFEASIBLE:
            logger.warning(
                f"No feasible solution found after {self.solution_time} seconds."
            )
            sys.exit()
        if self.status == OPTIMAL:
            logger.info(f"Optimal solution found after {self.solution_time} seconds.")
        if self.status == FEASIBLE:
            logger.info(
                f"Best feasible solution found after {self.solution_time} seconds."
            )

    def read_production_amounts(self):
        return {
            (pr, line, d): self.var_solution(self.production_amount[pr, line, d])
            for pr in PRODUCTS
            for line in PLANT_LINES
            for d in HORIZON
        }

    def read_stock(self):
        return {
            (pr, pl, d): sum(
                self.var_solution(self.stock_by_age[pr, pl, d, age])
                for age in range(min(d, PRODUCT_AGE[pr]))
            )
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        }

    def read_shortage(self):
        return {
            (pr, pl, d): self.var_solution(self.shortage[pr, pl, d])
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        }

    def read_sales(self):
        return {
            (pr, pl, d): sum(
                self.var_solution(self.sales_by_age[pr, pl, d, age])
                for age in range(min(d, PRODUCT_AGE[pr]))
            )
            for pr in PRODUCTS
            for pl in PLANTS
            for d in HORIZON
        }

    def var_solution(self, var):
        return var.solution_value()

    def set_runtime(self):
        self.math_model.set_time_limit(1000 * RUN_TIME)  # in milliseconds
