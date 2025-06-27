from src.backtester import Order, OrderBook
from typing import List
import numpy as np

class Trader:
    def __init__(self):
        """
        Initializes the Trader with parameters for an improved Market Making strategy.
        """
        self.position_limit = 20
        self.order_size = 5
        self.spread = 2  # Our desired profit margin per round trip
        self.risk_aversion = 0.1  # How much we adjust prices based on inventory
        
        # History for fair value calculation
        self.price_history = []
        self.sma_period = 10

    def run(self, state, current_position):
        """
        This function is called by the backtester on every time step and implements
        the improved market making logic with inventory skewing.
        """
        result = {}
        product = "PRODUCT"
        orders = []
        order_depth = state.order_depth

        if not order_depth.buy_orders or not order_depth.sell_orders:
            result[product] = orders
            return result

        # --- Fair Value Calculation ---
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        mid_price = (best_bid + best_ask) / 2
        
        self.price_history.append(mid_price)
        if len(self.price_history) > self.sma_period:
            self.price_history.pop(0)
        
        # Wait until we have enough data to calculate a stable fair value
        if len(self.price_history) < self.sma_period:
            result[product] = orders
            return result
            
        fair_value = np.mean(self.price_history)

        # --- Inventory Skewing Logic ---
        
        # 1. Define our ideal bid and ask prices around the fair value
        our_bid_price = fair_value - self.spread / 2
        our_ask_price = fair_value + self.spread / 2
        
        # 2. Calculate the inventory skew factor
        # This will be a value between -1 and 1
        inventory_skew = current_position / self.position_limit
        
        # 3. Adjust our prices based on the skew
        # If long (skew > 0), we lower both our bid and ask to encourage selling.
        # If short (skew < 0), we raise both our bid and ask to encourage buying.
        our_bid_price -= inventory_skew * self.risk_aversion
        our_ask_price -= inventory_skew * self.risk_aversion
        
        # Round to nearest integer price level
        our_bid_price = int(round(our_bid_price))
        our_ask_price = int(round(our_ask_price))

        # --- Order Placement with Skewed Sizes ---

        # Place a buy order if we are below our long position limit
        if current_position < self.position_limit:
            # When we are very long, place smaller buy orders
            buy_qty = int(self.order_size * (1 - inventory_skew))
            # Ensure we don't breach the position limit
            buy_qty = min(buy_qty, self.position_limit - current_position)
            if buy_qty > 0:
                orders.append(Order(product, our_bid_price, buy_qty))

        # Place a sell order if we are above our short position limit
        if current_position > -self.position_limit:
            # When we are very short, place smaller sell orders
            sell_qty = int(self.order_size * (1 + inventory_skew))
            # Ensure we don't breach the position limit
            sell_qty = min(sell_qty, self.position_limit + current_position)
            if sell_qty > 0:
                orders.append(Order(product, our_ask_price, -sell_qty))
        
        result[product] = orders
        return result
