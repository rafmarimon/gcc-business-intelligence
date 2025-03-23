#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ml_initializer')

class ReportAnalyzer:
    """
    Uses TensorFlow to analyze historical report data and generate forecasts
    for monthly and quarterly reports, with quantitative projections and insights.
    """
    
    def __init__(self, data_dir=None):
        """Initialize the report analyzer with TensorFlow."""
        # Set the data directory
        if data_dir:
            self.data_dir = data_dir
        else:
            # Use default directory
            home_dir = os.path.expanduser("~")
            default_data_dir = os.path.join(home_dir, "gp_reports", "data")
            self.data_dir = default_data_dir
            
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "processed"), exist_ok=True)
        
        # Check TensorFlow version and GPU availability
        logger.info(f"TensorFlow version: {tf.__version__}")
        logger.info(f"GPU available: {tf.config.list_physical_devices('GPU')}")
        
        # Initialize scalers for data normalization
        self.scalers = {}
        
        # Set model parameters
        self.seq_length = 30  # Number of days to use for prediction
        self.batch_size = 32
        self.epochs = 50
        
        logger.info(f"Report Analyzer initialized with data directory: {self.data_dir}")
    
    def extract_data_from_reports(self, reports_dir):
        """
        Extract structured data from historical reports.
        This function parses the reports to extract key metrics and trends.
        """
        logger.info(f"Extracting data from reports in {reports_dir}")
        
        # Initialize data containers
        economic_indicators = []
        industry_metrics = {}
        bilateral_trade = []
        
        # Walk through the reports directory
        for root, _, files in os.walk(reports_dir):
            for file in files:
                if file.endswith(".md"):
                    report_path = os.path.join(root, file)
                    
                    # Extract timestamp from filename
                    timestamp_str = file.replace("consolidated_report_", "").replace(".md", "")
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        report_date = timestamp.strftime("%Y-%m-%d")
                    except ValueError:
                        logger.warning(f"Could not parse timestamp from file: {file}")
                        continue
                    
                    # Parse report content
                    with open(report_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Extract economic indicators using simple pattern matching
                        # In a production environment, you would use NLP techniques for better extraction
                        gdp_growth = self._extract_metric(content, "GDP Growth")
                        inflation = self._extract_metric(content, "Inflation")
                        fdi = self._extract_metric(content, "Foreign Direct Investment")
                        
                        if gdp_growth or inflation or fdi:
                            economic_indicators.append({
                                "date": report_date,
                                "gdp_growth": gdp_growth,
                                "inflation": inflation,
                                "fdi": fdi
                            })
                        
                        # Extract industry-specific metrics
                        for industry in ["Technology", "Real Estate", "Energy", "Finance", "Healthcare"]:
                            industry_metric = self._extract_industry_metric(content, industry)
                            
                            if industry_metric:
                                if industry not in industry_metrics:
                                    industry_metrics[industry] = []
                                    
                                industry_metrics[industry].append({
                                    "date": report_date,
                                    "metric": industry_metric
                                })
                        
                        # Extract US-UAE trade data
                        trade_value = self._extract_trade_value(content)
                        if trade_value:
                            bilateral_trade.append({
                                "date": report_date,
                                "value": trade_value
                            })
        
        # Convert to DataFrames for easier processing
        economic_df = pd.DataFrame(economic_indicators)
        
        industry_dfs = {}
        for industry, metrics in industry_metrics.items():
            if metrics:
                industry_dfs[industry] = pd.DataFrame(metrics)
        
        trade_df = pd.DataFrame(bilateral_trade)
        
        # Save processed data
        if not economic_df.empty:
            economic_df.to_csv(os.path.join(self.data_dir, "processed", "economic_indicators.csv"), index=False)
            
        for industry, df in industry_dfs.items():
            if not df.empty:
                df.to_csv(os.path.join(self.data_dir, "processed", f"{industry.lower()}_metrics.csv"), index=False)
        
        if not trade_df.empty:
            trade_df.to_csv(os.path.join(self.data_dir, "processed", "bilateral_trade.csv"), index=False)
        
        logger.info(f"Extracted data from {len(economic_indicators)} reports")
        
        return {
            "economic": economic_df,
            "industry": industry_dfs,
            "trade": trade_df
        }
    
    def _extract_metric(self, content, metric_name):
        """Extract numeric metrics from report content using pattern matching."""
        import re
        
        # Look for patterns like "GDP Growth: 3.8%" or "Inflation: 2.1%"
        pattern = f"{metric_name}:? (\d+\.?\d*)%?"
        match = re.search(pattern, content)
        
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        
        return None
    
    def _extract_industry_metric(self, content, industry):
        """Extract industry-specific metrics."""
        import re
        
        # Look for sections about the specific industry
        industry_section_pattern = f"### {industry}(.*?)(###|\Z)"
        section_match = re.search(industry_section_pattern, content, re.DOTALL)
        
        if not section_match:
            return None
        
        section_text = section_match.group(1)
        
        # Look for metrics like "increased by 12%" or "growth of 15%"
        metric_patterns = [
            r"increased by (\d+\.?\d*)%",
            r"decreased by (\d+\.?\d*)%",
            r"growth of (\d+\.?\d*)%",
            r"decline of (\d+\.?\d*)%",
            r"(\d+\.?\d*)% increase",
            r"(\d+\.?\d*)% decrease"
        ]
        
        for pattern in metric_patterns:
            match = re.search(pattern, section_text)
            if match:
                try:
                    value = float(match.group(1))
                    # Check if this is a decrease metric
                    if "decrease" in pattern or "decline" in pattern:
                        value = -value
                    return value
                except ValueError:
                    continue
        
        return None
    
    def _extract_trade_value(self, content):
        """Extract US-UAE bilateral trade value."""
        import re
        
        # Look for patterns like "bilateral trade between the US and UAE reached $24.5 billion"
        patterns = [
            r"bilateral trade.*?reached \$(\d+\.?\d*) billion",
            r"trade.*?US and UAE.*?\$(\d+\.?\d*) billion",
            r"trade value.*?\$(\d+\.?\d*) billion"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def prepare_time_series_data(self, df, target_column, seq_length=None):
        """Prepare time series data for TensorFlow model."""
        if seq_length is None:
            seq_length = self.seq_length
            
        if df.empty:
            logger.warning("Empty DataFrame provided for time series preparation")
            return None, None, None, None
            
        # Sort by date
        df = df.sort_values('date')
        
        # Convert target column to numpy array
        data = df[target_column].values.reshape(-1, 1)
        
        # Normalize data
        scaler = MinMaxScaler(feature_range=(0, 1))
        data_scaled = scaler.fit_transform(data)
        self.scalers[target_column] = scaler
        
        # Create sequences
        X, y = [], []
        for i in range(len(data_scaled) - seq_length):
            X.append(data_scaled[i:i + seq_length])
            y.append(data_scaled[i + seq_length])
            
        X, y = np.array(X), np.array(y)
        
        # Split into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        return X_train, X_test, y_train, y_test
    
    def build_lstm_model(self, seq_length, features=1):
        """Build and compile LSTM model for time series forecasting."""
        model = keras.Sequential([
            keras.layers.LSTM(50, activation='relu', input_shape=(seq_length, features), return_sequences=True),
            keras.layers.Dropout(0.2),
            keras.layers.LSTM(50, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def train_forecasting_model(self, data, target_column, model_name):
        """Train a forecasting model for the specified metric."""
        logger.info(f"Training forecasting model for {target_column}")
        
        # Prepare the data
        X_train, X_test, y_train, y_test = self.prepare_time_series_data(data, target_column)
        
        if X_train is None:
            logger.warning(f"Insufficient data to train model for {target_column}")
            return None
            
        # Build the model
        model = self.build_lstm_model(self.seq_length)
        
        # Train the model
        history = model.fit(
            X_train, y_train,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_data=(X_test, y_test),
            verbose=1
        )
        
        # Save the model
        model_path = os.path.join(self.data_dir, "models", f"{model_name}.h5")
        model.save(model_path)
        
        # Save training history
        history_path = os.path.join(self.data_dir, "models", f"{model_name}_history.json")
        with open(history_path, 'w') as f:
            json.dump({
                "loss": [float(x) for x in history.history['loss']],
                "val_loss": [float(x) for x in history.history['val_loss']]
            }, f)
            
        logger.info(f"Model for {target_column} saved to {model_path}")
        
        return model
    
    def generate_forecast(self, data, target_column, model_name, forecast_steps=90):
        """Generate forecast for the next n days/periods."""
        logger.info(f"Generating {forecast_steps}-step forecast for {target_column}")
        
        # Load the model
        model_path = os.path.join(self.data_dir, "models", f"{model_name}.h5")
        
        if not os.path.exists(model_path):
            logger.warning(f"Model for {target_column} not found at {model_path}")
            return None
            
        model = keras.models.load_model(model_path)
        
        # Sort data by date and get the last sequence
        data = data.sort_values('date')
        last_sequence = data[target_column].values[-self.seq_length:].reshape(-1, 1)
        
        # Scale the sequence
        scaler = self.scalers.get(target_column)
        if scaler is None:
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaler.fit(data[target_column].values.reshape(-1, 1))
            self.scalers[target_column] = scaler
            
        last_sequence_scaled = scaler.transform(last_sequence)
        
        # Reshape for prediction
        current_batch = last_sequence_scaled.reshape(1, self.seq_length, 1)
        
        # Generate forecast steps
        forecast = []
        for _ in range(forecast_steps):
            # Predict the next value
            next_pred = model.predict(current_batch)[0]
            
            # Add prediction to forecast
            forecast.append(next_pred[0])
            
            # Update current batch with the new prediction
            current_batch = np.append(current_batch[:, 1:, :], [[next_pred]], axis=1)
            
        # Inverse transform the forecast
        forecast = np.array(forecast).reshape(-1, 1)
        forecast = scaler.inverse_transform(forecast)
        
        # Create date range for forecast
        last_date = pd.to_datetime(data['date'].iloc[-1])
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(forecast_steps)]
        
        # Create DataFrame with forecast
        forecast_df = pd.DataFrame({
            'date': forecast_dates,
            f'{target_column}_forecast': forecast.flatten()
        })
        
        return forecast_df
    
    def generate_monthly_report(self, reports_dir):
        """Generate monthly report with forecasts and insights."""
        logger.info("Generating monthly report with forecasts")
        
        # First, extract and process data from historical reports
        data = self.extract_data_from_reports(reports_dir)
        
        monthly_insights = {
            "economic_forecasts": {},
            "industry_forecasts": {},
            "trade_forecast": None,
            "correlations": {},
            "trends": {}
        }
        
        # Generate economic forecasts
        if not data["economic"].empty:
            for metric in ["gdp_growth", "inflation", "fdi"]:
                if metric in data["economic"].columns:
                    model_name = f"economic_{metric}"
                    
                    # Train model if needed
                    self.train_forecasting_model(data["economic"], metric, model_name)
                    
                    # Generate forecast
                    forecast = self.generate_forecast(data["economic"], metric, model_name, forecast_steps=30)
                    if forecast is not None:
                        monthly_insights["economic_forecasts"][metric] = forecast.to_dict(orient="records")
                        
                        # Calculate trend
                        current = data["economic"][metric].iloc[-1] if not data["economic"].empty else None
                        forecasted = forecast[f"{metric}_forecast"].iloc[-1] if not forecast.empty else None
                        
                        if current is not None and forecasted is not None:
                            change = ((forecasted - current) / current) * 100 if current != 0 else 0
                            monthly_insights["trends"][metric] = {
                                "current": float(current),
                                "forecasted": float(forecasted),
                                "change_percent": float(change),
                                "trend": "up" if change > 0 else "down"
                            }
        
        # Generate industry forecasts
        for industry, df in data["industry"].items():
            if not df.empty and "metric" in df.columns:
                model_name = f"industry_{industry.lower()}"
                
                # Train model if needed
                self.train_forecasting_model(df, "metric", model_name)
                
                # Generate forecast
                forecast = self.generate_forecast(df, "metric", model_name, forecast_steps=30)
                if forecast is not None:
                    monthly_insights["industry_forecasts"][industry] = forecast.to_dict(orient="records")
                    
                    # Calculate trend
                    current = df["metric"].iloc[-1] if not df.empty else None
                    forecasted = forecast["metric_forecast"].iloc[-1] if not forecast.empty else None
                    
                    if current is not None and forecasted is not None:
                        change = ((forecasted - current) / current) * 100 if current != 0 else 0
                        monthly_insights["trends"][f"industry_{industry.lower()}"] = {
                            "current": float(current),
                            "forecasted": float(forecasted),
                            "change_percent": float(change),
                            "trend": "up" if change > 0 else "down"
                        }
        
        # Generate trade forecast
        if not data["trade"].empty and "value" in data["trade"].columns:
            model_name = "bilateral_trade"
            
            # Train model if needed
            self.train_forecasting_model(data["trade"], "value", model_name)
            
            # Generate forecast
            forecast = self.generate_forecast(data["trade"], "value", model_name, forecast_steps=30)
            if forecast is not None:
                monthly_insights["trade_forecast"] = forecast.to_dict(orient="records")
                
                # Calculate trend
                current = data["trade"]["value"].iloc[-1] if not data["trade"].empty else None
                forecasted = forecast["value_forecast"].iloc[-1] if not forecast.empty else None
                
                if current is not None and forecasted is not None:
                    change = ((forecasted - current) / current) * 100 if current != 0 else 0
                    monthly_insights["trends"]["bilateral_trade"] = {
                        "current": float(current),
                        "forecasted": float(forecasted),
                        "change_percent": float(change),
                        "trend": "up" if change > 0 else "down"
                    }
        
        # Calculate correlations
        corr_data = {}
        
        # Add economic indicators
        for metric in ["gdp_growth", "inflation", "fdi"]:
            if not data["economic"].empty and metric in data["economic"].columns:
                corr_data[metric] = data["economic"][metric].values
        
        # Add industry metrics
        for industry, df in data["industry"].items():
            if not df.empty and "metric" in df.columns:
                corr_data[f"industry_{industry.lower()}"] = df["metric"].values
        
        # Add trade value
        if not data["trade"].empty and "value" in data["trade"].columns:
            corr_data["trade_value"] = data["trade"]["value"].values
        
        # Calculate correlation matrix if we have at least 2 metrics
        if len(corr_data) >= 2:
            # Ensure all arrays have the same length
            min_length = min(len(arr) for arr in corr_data.values())
            
            for key in corr_data:
                corr_data[key] = corr_data[key][:min_length]
            
            df_corr = pd.DataFrame(corr_data)
            corr_matrix = df_corr.corr().to_dict()
            monthly_insights["correlations"] = corr_matrix
        
        # Save insights to file
        insights_path = os.path.join(self.data_dir, f"monthly_insights_{datetime.now().strftime('%Y%m%d')}.json")
        with open(insights_path, 'w') as f:
            json.dump(monthly_insights, f, indent=2)
            
        logger.info(f"Monthly insights saved to {insights_path}")
        
        return monthly_insights
    
    def generate_quarterly_report(self, reports_dir):
        """Generate quarterly report with forecasts and insights."""
        logger.info("Generating quarterly report with forecasts")
        
        # First, generate monthly insights for base data
        monthly_insights = self.generate_monthly_report(reports_dir)
        
        # Extend forecasts for quarterly view (90 days)
        quarterly_insights = {
            "economic_forecasts": {},
            "industry_forecasts": {},
            "trade_forecast": None,
            "correlations": monthly_insights["correlations"],
            "trends": {},
            "quarterly_projections": {}
        }
        
        # Generate economic forecasts for 90 days
        data = self.extract_data_from_reports(reports_dir)
        
        if not data["economic"].empty:
            for metric in ["gdp_growth", "inflation", "fdi"]:
                if metric in data["economic"].columns:
                    model_name = f"economic_{metric}"
                    
                    # Generate 90-day forecast
                    forecast = self.generate_forecast(data["economic"], metric, model_name, forecast_steps=90)
                    if forecast is not None:
                        quarterly_insights["economic_forecasts"][metric] = forecast.to_dict(orient="records")
                        
                        # Calculate quarterly projection (average of next 90 days)
                        quarterly_avg = forecast[f"{metric}_forecast"].mean()
                        current_avg = data["economic"][metric].iloc[-90:].mean() if len(data["economic"]) > 90 else data["economic"][metric].mean()
                        
                        change = ((quarterly_avg - current_avg) / current_avg) * 100 if current_avg != 0 else 0
                        quarterly_insights["quarterly_projections"][metric] = {
                            "current_quarter_avg": float(current_avg),
                            "next_quarter_avg": float(quarterly_avg),
                            "change_percent": float(change),
                            "trend": "up" if change > 0 else "down"
                        }
        
        # Generate industry forecasts for 90 days
        for industry, df in data["industry"].items():
            if not df.empty and "metric" in df.columns:
                model_name = f"industry_{industry.lower()}"
                
                # Generate 90-day forecast
                forecast = self.generate_forecast(df, "metric", model_name, forecast_steps=90)
                if forecast is not None:
                    quarterly_insights["industry_forecasts"][industry] = forecast.to_dict(orient="records")
                    
                    # Calculate quarterly projection
                    quarterly_avg = forecast["metric_forecast"].mean()
                    current_avg = df["metric"].iloc[-90:].mean() if len(df) > 90 else df["metric"].mean()
                    
                    change = ((quarterly_avg - current_avg) / current_avg) * 100 if current_avg != 0 else 0
                    quarterly_insights["quarterly_projections"][f"industry_{industry.lower()}"] = {
                        "current_quarter_avg": float(current_avg),
                        "next_quarter_avg": float(quarterly_avg),
                        "change_percent": float(change),
                        "trend": "up" if change > 0 else "down"
                    }
        
        # Generate trade forecast for 90 days
        if not data["trade"].empty and "value" in data["trade"].columns:
            model_name = "bilateral_trade"
            
            # Generate 90-day forecast
            forecast = self.generate_forecast(data["trade"], "value", model_name, forecast_steps=90)
            if forecast is not None:
                quarterly_insights["trade_forecast"] = forecast.to_dict(orient="records")
                
                # Calculate quarterly projection
                quarterly_avg = forecast["value_forecast"].mean()
                current_avg = data["trade"]["value"].iloc[-90:].mean() if len(data["trade"]) > 90 else data["trade"]["value"].mean()
                
                change = ((quarterly_avg - current_avg) / current_avg) * 100 if current_avg != 0 else 0
                quarterly_insights["quarterly_projections"]["bilateral_trade"] = {
                    "current_quarter_avg": float(current_avg),
                    "next_quarter_avg": float(quarterly_avg),
                    "change_percent": float(change),
                    "trend": "up" if change > 0 else "down"
                }
        
        # Save insights to file
        insights_path = os.path.join(self.data_dir, f"quarterly_insights_{datetime.now().strftime('%Y%m%d')}.json")
        with open(insights_path, 'w') as f:
            json.dump(quarterly_insights, f, indent=2)
            
        logger.info(f"Quarterly insights saved to {insights_path}")
        
        return quarterly_insights
    
    def plot_forecast(self, historical_data, forecast_data, title, y_label, output_path):
        """Create visualization of forecast with historical data."""
        plt.figure(figsize=(12, 6))
        
        # Plot historical data
        plt.plot(historical_data['date'], historical_data.iloc[:, 1], 
                label='Historical', color='blue', linewidth=2)
        
        # Plot forecast
        plt.plot(forecast_data['date'], forecast_data.iloc[:, 1], 
                label='Forecast', color='red', linestyle='--', linewidth=2)
        
        # Add confidence interval
        # This is a simple estimation - in production you would calculate proper confidence intervals
        forecast_mean = forecast_data.iloc[:, 1].mean()
        forecast_std = forecast_data.iloc[:, 1].std()
        
        plt.fill_between(forecast_data['date'], 
                        forecast_data.iloc[:, 1] - forecast_std,
                        forecast_data.iloc[:, 1] + forecast_std,
                        color='red', alpha=0.2)
        
        # Add title and labels
        plt.title(title, fontsize=16)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Add legend
        plt.legend(fontsize=12)
        
        # Format x-axis dates
        plt.gcf().autofmt_xdate()
        
        # Add confidence interval label
        plt.text(0.05, 0.05, 'Shaded area represents ±1 standard deviation',
                transform=plt.gca().transAxes, fontsize=10, alpha=0.7)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        return output_path

if __name__ == "__main__":
    # Test the report analyzer
    analyzer = ReportAnalyzer()
    
    # Set the reports directory to the test reports
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generators", "test_reports")
    
    # Generate monthly report with forecasts and insights
    monthly_insights = analyzer.generate_monthly_report(reports_dir)
    
    if monthly_insights:
        print(f"Monthly insights generated with {len(monthly_insights['trends'])} trends")
    else:
        print("Failed to generate monthly insights") 