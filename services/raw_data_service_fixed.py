async def build_raw_orderbook_data(self, symbol: str) -> dict:
        """
        Build data terstruktur untuk /raw_orderbook yang akan diformat di Telegram.
        """
        try:
            # Normalisasi symbol
            base_symbol, futures_pair = self.api.resolve_orderbook_symbols(symbol)
            
            # Panggil 2 endpoint dengan graceful error handling
            snapshot_result = None
            binance_depth_result = None
            aggregated_depth_result = None
            
            try:
                snapshot_result = await self.api.get_orderbook_history(
                    base_symbol=base_symbol,
                    futures_pair=futures_pair,
                    exchange="Binance",
                    interval="1h",
                    limit=1
                )
            except Exception as e:
                logger.error(f"[RAW] Error fetching snapshot for {symbol}: {e}")
                snapshot_result = None
            
            try:
                binance_depth_result = await self.api.get_orderbook_ask_bids_history(
                    base_symbol=base_symbol,
                    futures_pair=futures_pair,
                    exchange="Binance",
                    interval="1d",
                    limit=100,
                    range_param="1"
                )
            except Exception as e:
                logger.error(f"[RAW] Error fetching Binance depth for {symbol}: {e}")
                binance_depth_result = None
            
            try:
                # Aggregated depth 1H
                aggregated_depth_result = await self.api.get_aggregated_orderbook_ask_bids_history(
                    base_symbol=base_symbol,
                    exchange_list="Binance",
                    interval="h1",
                    limit=500
                )
            except Exception as e:
                logger.error(f"[RAW] Error fetching aggregated depth for {symbol}: {e}")
                aggregated_depth_result = None
            
        except Exception as e:
            logger.error(f"[RAW] Error building raw orderbook data for {symbol}: {e}")
            # Return minimal structure on error
            return {
                "exchange": "Binance",
                "symbol": symbol,
                "interval_ob": "1h",
                "depth_range": "1%",
                "snapshot": {
                    "timestamp": None,
                    "top_bids": [],
                    "top_asks": [],
                    "best_bid_price": None,
                    "best_bid_qty": None,
                    "best_ask_price": None,
                    "best_ask_qty": None,
                    "spread": None,
                    "mid_price": None,
                },
                "binance_depth": {
                    "bids_usd": None,
                    "asks_usd": None,
                    "bids_qty": None,
                    "asks_qty": None,
                    "bias_label": None,
                },
                "aggregated_depth": {
                    "bids_usd": None,
                    "asks_usd": None,
                    "bids_qty": None,
                    "asks_qty": None,
                    "bias_label": None,
                },
                "analytics": {
                    "imbalance": {
                        "binance_1d": {"imbalance_pct": 0.0, "bias": "mixed"},
                        "aggregated_1h": {"imbalance_pct": 0.0, "bias": "mixed"}
                    },
                    "spoofing": {
                        "has_spoofing": False,
                        "type": None,
                        "level_price": None,
                        "size_usd": None,
                        "confidence": 0.0
                    },
                    "walls": {
                        "buy_walls": [],
                        "sell_walls": []
                    }
                }
            }

    def _compute_orderbook_analytics(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute institutional analytics for orderbook data
        """
        try:
            return {
                "imbalance": self._compute_orderbook_imbalance(orderbook_data),
                "spoofing": self._detect_spoofing(orderbook_data),
                "walls": self._detect_liquidity_walls(orderbook_data)
            }
        except Exception as e:
            logger.error(f"[RAW] Error computing orderbook analytics: {e}")
            return {
                "imbalance": {"binance_1d": {"imbalance_pct": 0.0, "bias": "mixed"}, "aggregated_1h": {"imbalance_pct": 0.0, "bias": "mixed"}},
                "spoofing": {"has_spoofing": False, "type": None, "level_price": None, "size_usd": None, "confidence": 0.0},
                "walls": {"buy_walls": [], "sell_walls": []}
            }

    def _compute_orderbook_imbalance(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute orderbook imbalance percentage for Binance 1D and Aggregated 1H
        """
        try:
            imbalance_data = {
                "binance_1d": {"imbalance_pct": 0.0, "bias": "mixed"},
                "aggregated_1h": {"imbalance_pct": 0.0, "bias": "mixed"}
            }
            
            # Binance 1D imbalance
            binance_depth = orderbook_data.get("binance_depth", {})
            if isinstance(binance_depth, dict):
                bids_usd = safe_float(binance_depth.get("bids_usd", 0))
                asks_usd = safe_float(binance_depth.get("asks_usd", 0))
                
                if bids_usd > 0 or asks_usd > 0:
                    total_usd = bids_usd + asks_usd
                    if total_usd > 0:
                        imbalance_pct = ((bids_usd - asks_usd) / total_usd) * 100
                        
                        if imbalance_pct > 10:
                            bias = "buyer"
                        elif imbalance_pct < -10:
                            bias = "seller"
                        else:
                            bias = "mixed"
                        
                        imbalance_data["binance_1d"] = {
                            "imbalance_pct": round(imbalance_pct, 1),
                            "bias": bias
                        }
            
            # Aggregated 1H imbalance
            aggregated_depth = orderbook_data.get("aggregated_depth", {})
            if isinstance(aggregated_depth, dict):
                agg_bids_usd = safe_float(aggregated_depth.get("bids_usd", 0))
                agg_asks_usd = safe_float(aggregated_depth.get("asks_usd", 0))
                
                if agg_bids_usd > 0 or agg_asks_usd > 0:
                    total_usd = agg_bids_usd + agg_asks_usd
                    if total_usd > 0:
                        imbalance_pct = ((agg_bids_usd - agg_asks_usd) / total_usd) * 100
                        
                        if imbalance_pct > 10:
                            bias = "buyer"
                        elif imbalance_pct < -10:
                            bias = "seller"
                        else:
                            bias = "mixed"
                        
                        imbalance_data["aggregated_1h"] = {
                            "imbalance_pct": round(imbalance_pct, 1),
                            "bias": bias
                        }
            
            return imbalance_data
            
        except Exception as e:
            logger.error(f"[RAW] Error computing orderbook imbalance: {e}")
            return {
                "binance_1d": {"imbalance_pct": 0.0, "bias": "mixed"},
                "aggregated_1h": {"imbalance_pct": 0.0, "bias": "mixed"}
            }

    def _detect_spoofing(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential spoofing (fake walls) in orderbook snapshot
        """
        try:
            spoofing_data = {
                "has_spoofing": False,
                "type": None,
                "level_price": None,
                "size_usd": None,
                "confidence": 0.0
            }
            
            # Get snapshot data
            snapshot = orderbook_data.get("snapshot", {})
            if not isinstance(snapshot, dict):
                return spoofing_data
            
            # Get bids and asks from snapshot
            bids = snapshot.get("top_bids", [])
            asks = snapshot.get("top_asks", [])
            
            if not bids and not asks:
                return spoofing_data
            
            # Convert to list of [price, qty] if needed
            bid_levels = []
            ask_levels = []
            
            # Process bids
            if isinstance(bids, list):
                for bid in bids:
                    if isinstance(bid, list) and len(bid) >= 2:
                        price = safe_float(bid[0])
                        qty = safe_float(bid[1])
                        if price > 0 and qty > 0:
                            bid_levels.append({"price": price, "qty": qty, "size_usd": price * qty})
                    elif isinstance(bid, dict):
                        price = safe_float(bid.get("price", 0))
                        qty = safe_float(bid.get("qty", bid.get("size", 0)))
                        if price > 0 and qty > 0:
                            bid_levels.append({"price": price, "qty": qty, "size_usd": price * qty})
            
            # Process asks
            if isinstance(asks, list):
                for ask in asks:
                    if isinstance(ask, list) and len(ask) >= 2:
                        price = safe_float(ask[0])
                        qty = safe_float(ask[1])
                        if price > 0 and qty > 0:
                            ask_levels.append({"price": price, "qty": qty, "size_usd": price * qty})
                    elif isinstance(ask, dict):
                        price = safe_float(ask.get("price", 0))
                        qty = safe_float(ask.get("qty", ask.get("size", 0)))
                        if price > 0 and qty > 0:
                            ask_levels.append({"price": price, "qty": qty, "size_usd": price * qty})
            
            # Calculate average size
            all_sizes = [level["size_usd"] for level in bid_levels + ask_levels if level["size_usd"] > 0]
            
            if not all_sizes:
                return spoofing_data
            
            avg_size = sum(all_sizes) / len(all_sizes)
            
            # Look for suspiciously large walls (5x average)
            spoofing_threshold = avg_size * 5
            
            # Check bids for spoofing
            for level in bid_levels:
                if level["size_usd"] > spoofing_threshold:
                    # Additional check: level should be far from mid price
                    mid_price = snapshot.get("mid_price")
                    if mid_price and abs(level["price"] - mid_price) / mid_price > 0.01:  # > 1% away
                        spoofing_data = {
                            "has_spoofing": True,
                            "type": "bid",
                            "level_price": level["price"],
                            "size_usd": level["size_usd"],
                            "confidence": min(0.8, level["size_usd"] / spoofing_threshold * 0.5)
                        }
                        return spoofing_data
            
            # Check asks for spoofing
            for level in ask_levels:
                if level["size_usd"] > spoofing_threshold:
                    # Additional check: level should be far from mid price
                    mid_price = snapshot.get("mid_price")
                    if mid_price and abs(level["price"] - mid_price) / mid_price > 0.01:  # > 1% away
                        spoofing_data = {
                            "has_spoofing": True,
                            "type": "ask",
                            "level_price": level["price"],
                            "size_usd": level["size_usd"],
                            "confidence": min(0.8, level["size_usd"] / spoofing_threshold * 0.5)
                        }
                        return spoofing_data
            
            return spoofing_data
            
        except Exception as e:
            logger.error(f"[RAW] Error detecting spoofing: {e}")
            return {
                "has_spoofing": False,
                "type": None,
                "level_price": None,
                "size_usd": None,
                "confidence": 0.0
            }

    def _detect_liquidity_walls(self, orderbook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect liquidity walls (large support/resistance levels) in orderbook
        """
        try:
            walls_data = {
                "buy_walls": [],
                "sell_walls": []
            }
            
            # Get snapshot data
            snapshot = orderbook_data.get("snapshot", {})
            if not isinstance(snapshot, dict):
                return walls_data
            
            # Get bids and asks from snapshot
            bids = snapshot.get("top_bids", [])
            asks = snapshot.get("top_asks", [])
            
            if not bids and not asks:
                return walls_data
            
            # Convert to list of wall candidates
            buy_walls = []
            sell_walls = []
            
            # Process bids (buy walls)
            if isinstance(bids, list):
                for bid in bids:
                    if isinstance(bid, list) and len(bid) >= 2:
                        price = safe_float(bid[0])
                        qty = safe_float(bid[1])
                        if price > 0 and qty > 0:
                            buy_walls.append({"price": price, "size_usd": price * qty})
                    elif isinstance(bid, dict):
                        price = safe_float(bid.get("price", 0))
                        qty = safe_float(bid.get("qty", bid.get("size", 0)))
                        if price > 0 and qty > 0:
                            buy_walls.append({"price": price, "size_usd": price * qty})
            
            # Process asks (sell walls)
            if isinstance(asks, list):
                for ask in asks:
                    if isinstance(ask, list) and len(ask) >= 2:
                        price = safe_float(ask[0])
                        qty = safe_float(ask[1])
                        if price > 0 and qty > 0:
                            sell_walls.append({"price": price, "size_usd": price * qty})
                    elif isinstance(ask, dict):
                        price = safe_float(ask.get("price", 0))
                        qty = safe_float(ask.get("qty", ask.get("size", 0)))
                        if price > 0 and qty > 0:
                            sell_walls.append({"price": price, "size_usd": price * qty})
            
            # Calculate average size for wall detection
            all_sizes = [wall["size_usd"] for wall in buy_walls + sell_walls if wall["size_usd"] > 0]
            
            if not all_sizes:
                return walls_data
            
            avg_size = sum(all_sizes) / len(all_sizes)
            wall_threshold = avg_size * 5  # 5x average = wall
            
            # Filter for significant walls
            significant_buy_walls = [
                wall for wall in buy_walls 
                if wall["size_usd"] > wall_threshold
            ]
            
            significant_sell_walls = [
                wall for wall in sell_walls 
                if wall["size_usd"] > wall_threshold
            ]
            
            # Sort by size (largest first) and limit to top 3
            significant_buy_walls.sort(key=lambda x: x["size_usd"], reverse=True)
            significant_sell_walls.sort(key=lambda x: x["size_usd"], reverse=True)
            
            walls_data = {
                "buy_walls": significant_buy_walls[:3],
                "sell_walls": significant_sell_walls[:3]
            }
            
            return walls_data
            
        except Exception as e:
            logger.error(f"[RAW] Error detecting liquidity walls: {e}")
            return {
                "buy_walls": [],
                "sell_walls": []
            }
