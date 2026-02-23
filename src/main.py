import argparse
import sys
import logging
from src.core.config import load_config, ConfigError
from src.exchange.binance import BinanceSpotAdapter
from src.bot.loop import GridBotOrchestrator

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def main():
    setup_logging()
    logger = logging.getLogger("main")
    
    parser = argparse.ArgumentParser(description="GridBot MVP CLI")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to configuration file")
    parser.add_argument("--state", type=str, default="state.json", help="Path to the bot state file")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no real orders)")
    parser.add_argument("--run-once", action="store_true", help="Run a single tick and exit (mostly for testing)")
    args = parser.parse_args()

    try:
        config = load_config(args.config, args.dry_run)
    except ConfigError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)

    logger.info("Starting GridBot MVP")
    logger.info(f"Dry run mode: {config.dry_run}")
    logger.info(f"Grid setup: {config.grid.symbol} ({config.grid.mode}) with {config.grid.grid_intervals} intervals")
        
    try:
        exchange = BinanceSpotAdapter(
            api_key=config.api_key or "",
            api_secret=config.api_secret or "",
            testnet=False # Spot Testnet not natively reliable for all pairs, but could be dynamic
        )
        
        bot = GridBotOrchestrator(config, exchange, state_file=args.state)
        bot.initialize()
        
        if args.run_once:
            logger.info("Running a single tick for validation...")
            bot.execute_tick()
            logger.info("Tick executed successfully.")
        else:
            logger.info("Entering continuous bot loop... (Press Ctrl+C to stop)")
            bot.run_loop()
        
    except KeyboardInterrupt:
        logger.info("\n--- END OF RUN SUMMARY ---")
        if 'bot' in locals() and bot.state:
            logger.info(f"Final Phase: {bot.state.phase.value}")
            logger.info(f"Realized PnL: {bot.state.realized_pnl:.4f}")
            logger.info(f"Active Order: {bot.state.active_order.order_id if bot.state.active_order else 'None'}")
        logger.info("Graceful shutdown complete.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Bot execution failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
