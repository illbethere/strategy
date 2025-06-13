import time
import threading
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime, date
from xtquant.xtdata import subscribe_quote, get_market_data_ex
plt.rcParams['axes.unicode_minus'] = False  # Fix negative sign display issue

class StockMonitor:
    """Stock/Futures Real-time Monitoring and Visualization System"""
    
    def __init__(self, symbols, update_interval=5):
        """
        Initialize the monitoring system
        :param symbols: List of stock/futures codes (e.g., ["IF2506.IF", "000300.SH"])
        :param update_interval: Data update interval (minutes), default 5 minutes
        """
        self.symbols = symbols  # List of codes to monitor
        self.update_interval = update_interval * 60  # Convert to seconds
        self.running = False  # System running status
        self.data_dict = {}  # Store real-time data
        self.lock = threading.Lock()  # Thread lock
        self.figures = {}  # Store chart objects
        
        # Ensure there are exactly two codes (futures and underlying)
        if len(symbols) != 2:
            raise ValueError("Please provide two codes: [Futures Code, Underlying Code]")
        
        self.future_symbol = symbols[0]  # Futures code
        self.underlying_symbol = symbols[1]  # Underlying code
        
        # Initialize data storage
        self._init_data_storage()
        
    def _init_data_storage(self):
        """Initialize data storage structure"""
        for symbol in self.symbols:
            self.data_dict[symbol] = pd.DataFrame(columns=['time', 'close'])
    
    def start_subscription(self):
        """Start data subscription"""
        for symbol in self.symbols:
            sub_id = subscribe_quote(
                stock_code=symbol,
                period='1m',
                count=-1,
                callback=self._data_callback
            )
            print(f"Subscribed to {symbol}, Subscription ID: {sub_id}")
    
    def _data_callback(self, datas):
        """Data callback function: update in-memory data"""
        with self.lock:
            for symbol, data_list in datas.items():
                if symbol in self.data_dict and data_list:
                    # Convert to DataFrame
                    new_data = pd.DataFrame(data_list)
                    
                    # Ensure new data contains necessary columns
                    if 'time' not in new_data.columns or 'close' not in new_data.columns:
                        print(f"Warning: Received data for {symbol} missing necessary columns")
                        continue
                    
                    # Filter out rows with empty close prices
                    new_data = new_data.dropna(subset=['close'])
                    
                    if new_data.empty:
                        continue
                    
                    self.data_dict[symbol] = pd.concat(
                        [self.data_dict[symbol], new_data], 
                        ignore_index=True
                    ).drop_duplicates(subset=['time'], keep='last')
                    
                    # Limit data to 300 rows
                    self.data_dict[symbol] = self.data_dict[symbol].tail(300)
    
    def start_updater(self):
        """Start data update thread"""
        def update_loop():
            while self.running:
                self._force_update_data()
                time.sleep(self.update_interval)
        
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
    
    def _force_update_data(self):
        """Force data update"""
        print(f"[{datetime.now()}] Starting data update")
        today = date.today()
        today_open = today.strftime("%Y%m%d") + '093000'
        try:
            data = get_market_data_ex(
                ['time', 'close'], self.symbols, period='1m', count=300, start_time=today_open, 
            )
            with self.lock:
                for symbol, df in data.items():
                    if symbol in self.data_dict and not df.empty:
                        # Ensure data contains necessary columns
                        if 'time' not in df.columns or 'close' not in df.columns:
                            print(f"Warning: Updated data for {symbol} missing necessary columns")
                            continue
                            
                        # Filter out rows with empty close prices
                        df = df.dropna(subset=['close'])
                        
                        if df.empty:
                            continue
                            
                        self.data_dict[symbol] = df
        except Exception as e:
            print(f"Data update error: {str(e)}")
    
    def create_charts(self):
        """Create charts"""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), 
                                      gridspec_kw={'height_ratios': [3, 3, 2]})
        fig.suptitle(f"Real-time Monitoring and Basis Analysis of {self.future_symbol} and {self.underlying_symbol}", fontsize=16)
        
        # Futures price subplot
        ax1.set_title(f"{self.future_symbol} Futures Price", fontsize=12)
        ax1.grid(True)
        ax1.set_ylabel("Price")
        
        # Underlying price subplot
        ax2.set_title(f"{self.underlying_symbol} Underlying Price", fontsize=12)
        ax2.grid(True)
        ax2.set_ylabel("Price")
        
        # Basis subplot
        ax3.set_title("Basis = Futures Price - Underlying Price", fontsize=12)
        ax3.grid(True)
        ax3.set_ylabel("Basis Value")
        ax3.set_xlabel("Time")
        
        # Save chart objects
        self.figures = {
            'fig': fig,
            'axes': (ax1, ax2, ax3),
            'lines': {
                'future_close': ax1.plot([], [], 'b-', label='Futures Close')[0],
                'underlying_close': ax2.plot([], [], 'r-', label='Underlying Close')[0],
                'basis': ax3.plot([], [], 'g-', label='Basis')[0],
                'basis_zero_line': ax3.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            },
            'last_updated': ax1.text(0.01, 0.95, '', transform=ax1.transAxes),
            'basis_stats': ax3.text(0.01, 0.90, '', transform=ax3.transAxes)
        }
        
        ax1.legend()
        ax2.legend()
        ax3.legend()
    
    def update_chart(self, frame):
        """Update chart data"""
        with self.lock:
            # Get futures and underlying data
            future_data = self.data_dict.get(self.future_symbol, pd.DataFrame())
            underlying_data = self.data_dict.get(self.underlying_symbol, pd.DataFrame())
            
            if future_data.empty or underlying_data.empty:
                return
            
            # Ensure both datasets have common time points
            common_times = set(future_data['time']).intersection(set(underlying_data['time']))
            if not common_times:
                return
                
            # Filter data by common time points
            future_common = future_data[future_data['time'].isin(common_times)]
            underlying_common = underlying_data[underlying_data['time'].isin(common_times)]
            
            # Sort by time
            future_common = future_common.sort_values('time')
            underlying_common = underlying_common.sort_values('time')
            
            # Convert time to readable format
            future_common['time_readable'] = pd.to_datetime(future_common['time'].astype(str), format='%Y%m%d%H%M%S')
            underlying_common['time_readable'] = pd.to_datetime(underlying_common['time'].astype(str), format='%Y%m%d%H%M%S')
            
            # Get chart objects
            fig_data = self.figures
            ax1, ax2, ax3 = fig_data['axes']
            lines = fig_data['lines']
            
            # Update futures price line
            x = future_common['time_readable']
            lines['future_close'].set_data(x, future_common['close'])
            
            # Update underlying price line
            lines['underlying_close'].set_data(x, underlying_common['close'])
            
            # Calculate basis = futures price - underlying price
            basis = future_common['close'].values - underlying_common['close'].values
            lines['basis'].set_data(x, basis)
            
            # Update axes ranges
            for ax in [ax1, ax2, ax3]:
                ax.relim()
                ax.autoscale_view()
            
            # Update last updated time
            last_time = future_common['time_readable'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S')
            fig_data['last_updated'].set_text(f'Last Updated: {last_time}')
            
            # Update basis statistics
            current_basis = basis[-1]
            min_basis = basis.min()
            max_basis = basis.max()
            avg_basis = basis.mean()
            
            stats_text = (f'Current Basis: {current_basis:.2f} | '
                         f'Min: {min_basis:.2f} | '
                         f'Max: {max_basis:.2f} | '
                         f'Avg: {avg_basis:.2f}')
            
            fig_data['basis_stats'].set_text(stats_text)
            
            # Rotate x-axis labels
            for tick in ax3.get_xticklabels():
                tick.set_rotation(45)
            
            # Refresh canvas
            fig_data['fig'].canvas.draw_idle()
    
    def start_monitoring(self):
        """Start monitoring system"""
        self.running = True
        self.start_subscription()
        self.start_updater()
        self.create_charts()
        
        print(f"System running: Monitoring {self.symbols}, Refresh Interval: {self.update_interval/60} minutes")
        
        # Create animation update
        self.animation = FuncAnimation(
            self.figures['fig'],
            self.update_chart,
            interval=5000,  # Refresh every 5 seconds
            cache_frame_data=False
        )
        
        # Display charts
        plt.tight_layout()
        plt.subplots_adjust(top=0.92)  # Make room for title
        plt.show()
    
    def stop_monitoring(self):
        """Stop monitoring system"""
        self.running = False
        print("System stopped")

# Usage example
if __name__ == "__main__":
    # Configuration parameters
    SYMBOLS = ["IF2506.IF", "000300.SH"]  # Futures and index codes
    UPDATE_INTERVAL = 1  # Update every 1 minute
    
    # Create monitoring instance
    monitor = StockMonitor(SYMBOLS, UPDATE_INTERVAL)
    
    try:
        monitor.start_monitoring()
    
    except KeyboardInterrupt:
        print("\nUser interrupted, stopping system...")
        monitor.stop_monitoring()
    
    except Exception as e:
        print(f"System error: {str(e)}")
        monitor.stop_monitoring()    