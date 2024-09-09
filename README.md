# Dairy Production Optimization

## Project Overview

This project aims to optimize the production plan for a dairy company. The company faces challenges in meeting daily
demand while managing production capacity and minimizing waste due to the short shelf life of products.
The optimization model is formulated as a Linear Program in Integer Numbers.

## Problem Description

The main constraints and requirements for the production plan are as follows:

- Daily demand must be met.
- Production capacity of the lines cannot be exceeded.
- A minimum stock level must be maintained for each product.
- Production is allowed only if it exceeds a certain Minimum Order Quantity (MOQ) defined by product and production
  line.
- Production should be a multiple of a given lot size defined by product and production line.
- Products can be produced on several lines, but each product has a preferred line.
- Demand is expressed in units, while production capacity is expressed in hours. Each product has a production rate
  related to the production line.
- Shortage and stock are allowed to avoid infeasibility.

## Project Structure

- `main.py`: Main script to run the optimization model and generate production plans.
- `model.py`: Contains the `OptimizationModel` class that defines and solves the optimization problem.
- `logger.py`: Logging utility for the project.
- `base.py`: Contains the classes that defines all the objects in the problem.
