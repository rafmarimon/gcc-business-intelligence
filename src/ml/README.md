# Machine Learning for Business Intelligence Reports

This module adds TensorFlow-based machine learning capabilities to the Global Possibilities Business Intelligence Platform, enabling the system to learn from historical reports and generate monthly and quarterly forecasts with quantitative projections and insights.

## Overview

The ML module provides the following capabilities:

1. **Data Extraction**: Automatically extract structured economic data from historical reports
2. **Pattern Recognition**: Identify trends and relationships in economic indicators over time
3. **Time Series Forecasting**: Generate forecasts for economic metrics using LSTM neural networks
4. **Correlation Analysis**: Identify relationships between different economic indicators
5. **Automated Report Generation**: Create comprehensive forecast reports with visualizations

## Getting Started

### Prerequisites

The following packages are required (available in requirements.txt):
- TensorFlow 2.12.0 or higher
- pandas
- numpy
- matplotlib
- scikit-learn
- h5py

### Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Ensure you have a collection of historical reports for the system to analyze (at least 10-15 reports for meaningful analysis)

### Usage

#### Basic Usage

```python
from src.ml.report_integration import MLReportIntegration

# Initialize with your reports directory
integration = MLReportIntegration(reports_dir="/path/to/reports")

# Generate a monthly forecast report
md_path, html_path, pdf_path = integration.generate_monthly_forecast_report()

# Generate a quarterly forecast report
md_path, html_path, pdf_path = integration.generate_quarterly_forecast_report()
```

#### Running the Test Script

A test script is provided to demonstrate the functionality with generated test data:

```
python src/ml/test_ml_reports.py
```

This will:
1. Generate sample test data with economic patterns
2. Use TensorFlow to analyze data and identify trends
3. Generate monthly and quarterly forecasts
4. Create reports in markdown, HTML, and PDF formats

## How It Works

### Data Extraction

The system analyzes historical reports to extract key economic indicators:
- GDP growth percentages
- Inflation rates
- Foreign Direct Investment trends
- Industry-specific growth metrics
- Bilateral trade values

### Machine Learning Models

1. **LSTM Networks**: Long Short-Term Memory neural networks are used for time series forecasting, trained on historical data sequences
2. **Sequence Prediction**: Models predict future values for each economic indicator
3. **Correlation Analysis**: Statistical analysis identifies relationships between different metrics

### Report Generation

The system automatically generates comprehensive reports that include:
- Executive summary with key takeaways
- Detailed forecasts for each economic indicator
- Industry-specific projections
- Trade relationship forecasts
- Correlation analysis
- Data visualizations (charts and heatmaps)
- LinkedIn post suggestions based on insights

## Customization

### Model Parameters

You can adjust model parameters in `ml_initializer.py`:
- `seq_length`: Number of historical data points to use for prediction
- `epochs`: Number of training epochs
- `batch_size`: Batch size for training

### Adding New Metrics

To track additional economic indicators:
1. Add patterns to extract the new metrics in the `_extract_metric()` method
2. Add the new metrics to the forecast generation functions

## Limitations and Considerations

- **Data Requirements**: Accurate forecasting requires sufficient historical data (at least 3-6 months of regular reports)
- **Consistency**: Report format should be consistent for optimal data extraction
- **Computational Requirements**: Training models can be resource-intensive; consider using GPU acceleration for larger datasets
- **Forecast Horizon**: Short-term forecasts (30-90 days) are generally more reliable than long-term projections

## Integration with Existing Systems

The ML module integrates seamlessly with the existing report generation pipeline:
- Reports continue to use the same formatting and structure
- ML insights are added as additional sections
- Generated forecasts can be distributed through the same channels

## Future Enhancements

Planned improvements include:
- Advanced NLP for better data extraction from unstructured text
- Multiple model ensemble for improved forecast accuracy
- Anomaly detection for unusual economic patterns
- Interactive dashboards for forecast visualization
- Automated alerts for significant forecast changes 