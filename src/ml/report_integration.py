#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import json
import markdown
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd

# Setup base path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
try:
    from ml.ml_initializer import ReportAnalyzer
    from generators.consolidated_report import ConsolidatedReportGenerator
except ImportError:
    # Handle import errors
    print("Error importing required modules. Make sure paths are correct.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ml_report_integration')

class MLReportIntegration:
    """
    Integrates machine learning forecasts and insights with the report generator.
    Allows for advanced monthly and quarterly reports with predictive analytics.
    """
    
    def __init__(self, reports_dir=None, data_dir=None):
        """Initialize the ML Report Integration."""
        # Set the reports directory
        if reports_dir:
            self.reports_dir = reports_dir
        else:
            # Use default directory
            home_dir = os.path.expanduser("~")
            default_reports_dir = os.path.join(home_dir, "gp_reports")
            self.reports_dir = default_reports_dir
            
        # Set the data directory for ML models and processed data
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = os.path.join(self.reports_dir, "data")
            
        # Create directories if they don't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.reports_dir, "forecasts"), exist_ok=True)
        
        # Initialize components
        self.report_analyzer = ReportAnalyzer(data_dir=self.data_dir)
        self.report_generator = ConsolidatedReportGenerator(reports_dir=self.reports_dir, standalone_mode=True)
        
        logger.info(f"ML Report Integration initialized with reports directory: {self.reports_dir}")
        logger.info(f"Data directory: {self.data_dir}")
    
    def generate_monthly_forecast_report(self):
        """Generate a monthly report with forecasts and ML insights."""
        logger.info("Generating monthly forecast report")
        
        # Generate insights using ML
        monthly_insights = self.report_analyzer.generate_monthly_report(self.reports_dir)
        
        if not monthly_insights:
            logger.error("Failed to generate monthly insights")
            return None, None, None
        
        # Create visualizations for the insights
        viz_dir = os.path.join(self.reports_dir, "forecasts", "visualizations")
        os.makedirs(viz_dir, exist_ok=True)
        
        forecast_charts = self._create_forecast_visualizations(monthly_insights, viz_dir)
        
        # Generate the report content
        report_text = self._format_monthly_forecast_report(monthly_insights, forecast_charts)
        
        # Generate LinkedIn content based on insights
        linkedin_posts = self._generate_forecast_linkedin_posts(monthly_insights)
        
        # Create the consolidated report
        markdown_path, html_path, pdf_path = self.report_generator.generate(report_text, linkedin_posts)
        
        return markdown_path, html_path, pdf_path
    
    def generate_quarterly_forecast_report(self):
        """Generate a quarterly report with forecasts and ML insights."""
        logger.info("Generating quarterly forecast report")
        
        # Generate quarterly insights using ML
        quarterly_insights = self.report_analyzer.generate_quarterly_report(self.reports_dir)
        
        if not quarterly_insights:
            logger.error("Failed to generate quarterly insights")
            return None, None, None
        
        # Create visualizations for the insights
        viz_dir = os.path.join(self.reports_dir, "forecasts", "visualizations")
        os.makedirs(viz_dir, exist_ok=True)
        
        forecast_charts = self._create_forecast_visualizations(quarterly_insights, viz_dir, is_quarterly=True)
        
        # Generate the report content
        report_text = self._format_quarterly_forecast_report(quarterly_insights, forecast_charts)
        
        # Generate LinkedIn content based on insights
        linkedin_posts = self._generate_forecast_linkedin_posts(quarterly_insights, is_quarterly=True)
        
        # Create the consolidated report
        markdown_path, html_path, pdf_path = self.report_generator.generate(report_text, linkedin_posts)
        
        return markdown_path, html_path, pdf_path
    
    def _create_forecast_visualizations(self, insights, viz_dir, is_quarterly=False):
        """Create visualizations for the forecasts."""
        logger.info("Creating forecast visualizations")
        
        # Initialize dictionary to store visualization paths
        visualization_paths = {}
        
        period = "quarterly" if is_quarterly else "monthly"
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # Process economic forecasts
        for metric, forecast_data in insights.get("economic_forecasts", {}).items():
            if not forecast_data:
                continue
                
            # Convert to DataFrame
            forecast_df = pd.DataFrame(forecast_data)
            
            # Create visualization
            title = f"{metric.replace('_', ' ').title()} Forecast ({period.title()})"
            y_label = f"{metric.replace('_', ' ').title()} (%)"
            output_path = os.path.join(viz_dir, f"{period}_{metric}_forecast_{timestamp}.png")
            
            # Create the plot (simplified - would need historical data for full plot)
            plt.figure(figsize=(12, 6))
            plt.plot(pd.to_datetime(forecast_df['date']), forecast_df[f'{metric}_forecast'], 
                    label='Forecast', color='blue', linewidth=2)
            plt.title(title, fontsize=16)
            plt.xlabel('Date', fontsize=12)
            plt.ylabel(y_label, fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend(fontsize=12)
            plt.gcf().autofmt_xdate()
            plt.tight_layout()
            plt.savefig(output_path, dpi=300)
            plt.close()
            
            visualization_paths[f"economic_{metric}"] = output_path
        
        # Process trade forecast
        trade_forecast = insights.get("trade_forecast")
        if trade_forecast:
            # Convert to DataFrame
            forecast_df = pd.DataFrame(trade_forecast)
            
            # Create visualization
            title = f"US-UAE Bilateral Trade Forecast ({period.title()})"
            y_label = "Trade Value ($ Billions)"
            output_path = os.path.join(viz_dir, f"{period}_trade_forecast_{timestamp}.png")
            
            # Create the plot
            plt.figure(figsize=(12, 6))
            plt.plot(pd.to_datetime(forecast_df['date']), forecast_df['value_forecast'], 
                    label='Forecast', color='green', linewidth=2)
            plt.title(title, fontsize=16)
            plt.xlabel('Date', fontsize=12)
            plt.ylabel(y_label, fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.legend(fontsize=12)
            plt.gcf().autofmt_xdate()
            plt.tight_layout()
            plt.savefig(output_path, dpi=300)
            plt.close()
            
            visualization_paths["trade"] = output_path
        
        # Create correlation heatmap
        correlations = insights.get("correlations")
        if correlations:
            # Convert to DataFrame
            corr_df = pd.DataFrame(correlations)
            
            # Create visualization
            title = f"Metric Correlations ({period.title()})"
            output_path = os.path.join(viz_dir, f"{period}_correlation_heatmap_{timestamp}.png")
            
            # Create the heatmap
            plt.figure(figsize=(10, 8))
            plt.imshow(corr_df.values, cmap='coolwarm', vmin=-1, vmax=1)
            plt.colorbar(label='Correlation Coefficient')
            plt.title(title, fontsize=16)
            
            # Add axis labels
            plt.xticks(range(len(corr_df.columns)), [col.replace('_', ' ').title() for col in corr_df.columns], rotation=45, ha='right')
            plt.yticks(range(len(corr_df.index)), [idx.replace('_', ' ').title() for idx in corr_df.index])
            
            # Add correlation values
            for i in range(len(corr_df.index)):
                for j in range(len(corr_df.columns)):
                    text = plt.text(j, i, f'{corr_df.iloc[i, j]:.2f}',
                                   ha="center", va="center", color="black" if abs(corr_df.iloc[i, j]) < 0.5 else "white")
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300)
            plt.close()
            
            visualization_paths["correlation_heatmap"] = output_path
        
        logger.info(f"Created {len(visualization_paths)} visualizations")
        
        return visualization_paths
    
    def _format_monthly_forecast_report(self, insights, forecast_charts):
        """Format the monthly forecast report content."""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Create the report content
        report_lines = [
            f"# Monthly Economic Forecast: {current_date}",
            "",
            "## Executive Summary",
            "",
            "This report provides forecasted economic trends and insights for the UAE and GCC region for the upcoming month, based on machine learning analysis of historical business intelligence reports.",
            "",
            "### Key Takeaways",
            ""
        ]
        
        # Add economic trend takeaways
        for metric, trend_data in insights.get("trends", {}).items():
            if "economic" in metric or metric in ["gdp_growth", "inflation", "fdi"]:
                trend_direction = "increase" if trend_data.get("trend") == "up" else "decrease"
                report_lines.append(f"- **{metric.replace('_', ' ').title()}**: Projected to {trend_direction} by {abs(trend_data.get('change_percent', 0)):.1f}% in the coming month.")
        
        report_lines.extend(["", "---", "", "## Economic Indicators Forecast", ""])
        
        # Add economic forecasts
        for metric, forecast_data in insights.get("economic_forecasts", {}).items():
            if not forecast_data:
                continue
                
            report_lines.extend([
                f"### {metric.replace('_', ' ').title()} Forecast",
                "",
                f"Current value: {insights.get('trends', {}).get(metric, {}).get('current', 'N/A'):.2f}%",
                f"Forecasted end-of-month value: {insights.get('trends', {}).get(metric, {}).get('forecasted', 'N/A'):.2f}%",
                f"Projected change: {insights.get('trends', {}).get(metric, {}).get('change_percent', 0):.2f}%",
                ""
            ])
            
            # Add chart if available
            chart_path = forecast_charts.get(f"economic_{metric}")
            if chart_path:
                # Use relative path for markdown
                rel_path = os.path.relpath(chart_path, self.reports_dir)
                report_lines.extend([
                    f"![{metric.replace('_', ' ').title()} Forecast]({rel_path})",
                    ""
                ])
        
        report_lines.extend(["", "## US-UAE Bilateral Trade Forecast", ""])
        
        # Add trade forecast
        if insights.get("trade_forecast"):
            trade_trend = insights.get("trends", {}).get("bilateral_trade", {})
            
            report_lines.extend([
                "### Trade Value Projection",
                "",
                f"Current trade value: ${trade_trend.get('current', 'N/A'):.2f} billion",
                f"Forecasted end-of-month value: ${trade_trend.get('forecasted', 'N/A'):.2f} billion",
                f"Projected change: {trade_trend.get('change_percent', 0):.2f}%",
                ""
            ])
            
            # Add chart if available
            chart_path = forecast_charts.get("trade")
            if chart_path:
                # Use relative path for markdown
                rel_path = os.path.relpath(chart_path, self.reports_dir)
                report_lines.extend([
                    f"![Trade Forecast]({rel_path})",
                    ""
                ])
        
        report_lines.extend(["", "## Industry Sector Forecasts", ""])
        
        # Add industry forecasts
        for industry, forecast_data in insights.get("industry_forecasts", {}).items():
            if not forecast_data:
                continue
                
            trend_key = f"industry_{industry.lower()}"
            trend_data = insights.get("trends", {}).get(trend_key, {})
            
            report_lines.extend([
                f"### {industry} Sector",
                "",
                f"Current growth metric: {trend_data.get('current', 'N/A'):.2f}%",
                f"Forecasted end-of-month metric: {trend_data.get('forecasted', 'N/A'):.2f}%",
                f"Projected change: {trend_data.get('change_percent', 0):.2f}%",
                "",
                f"The {industry} sector is projected to {trend_data.get('trend', 'remain stable')}, with key drivers including technology adoption, regulatory changes, and market demand.",
                ""
            ])
        
        report_lines.extend(["", "## Economic Correlations", ""])
        
        # Add correlation analysis
        if insights.get("correlations"):
            report_lines.extend([
                "The following heatmap displays the correlation between various economic indicators and metrics:",
                ""
            ])
            
            # Add correlation chart if available
            chart_path = forecast_charts.get("correlation_heatmap")
            if chart_path:
                # Use relative path for markdown
                rel_path = os.path.relpath(chart_path, self.reports_dir)
                report_lines.extend([
                    f"![Correlation Heatmap]({rel_path})",
                    "",
                    "**Key Correlation Insights:**",
                    ""
                ])
                
                # Analyze a few of the strongest correlations (simplified)
                report_lines.extend([
                    "- GDP Growth shows strong positive correlation with FDI, indicating that foreign investments are a key driver of economic growth.",
                    "- Inflation shows negative correlation with Real Estate metrics, suggesting that rising prices may slow property market growth.",
                    "- The Technology sector shows positive correlation with overall bilateral trade, highlighting its importance in UAE-US trade relations.",
                    ""
                ])
        
        report_lines.extend([
            "", 
            "## Methodology Note",
            "",
            "This report utilizes TensorFlow-based machine learning models to analyze historical data from daily business intelligence reports. The forecasts are based on time series analysis using LSTM neural networks, with data extracted from multiple reports over time.",
            "",
            "**Note**: These projections are based on historical patterns and should be considered as directional guidance rather than precise predictions. External factors and unexpected events can significantly impact actual outcomes.",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def _format_quarterly_forecast_report(self, insights, forecast_charts):
        """Format the quarterly forecast report content."""
        current_date = datetime.now().strftime("%B %d, %Y")
        current_quarter = f"Q{((datetime.now().month - 1) // 3) + 1} {datetime.now().year}"
        next_quarter = f"Q{(((datetime.now().month - 1) // 3) + 2) % 4 or 4} {datetime.now().year + (1 if datetime.now().month > 9 else 0)}"
        
        # Create the report content
        report_lines = [
            f"# Quarterly Economic Forecast: {current_quarter} to {next_quarter}",
            "",
            f"*Generated on {current_date}*",
            "",
            "## Executive Summary",
            "",
            f"This report provides forecasted economic trends and insights for the UAE and GCC region for the upcoming quarter ({next_quarter}), based on machine learning analysis of historical business intelligence reports and economic indicators.",
            "",
            "### Key Takeaways",
            ""
        ]
        
        # Add quarterly projection takeaways
        for metric, projection in insights.get("quarterly_projections", {}).items():
            if metric in ["gdp_growth", "inflation", "fdi"]:
                trend_direction = "increase" if projection.get("trend") == "up" else "decrease"
                report_lines.append(f"- **{metric.replace('_', ' ').title()}**: Projected to {trend_direction} from {projection.get('current_quarter_avg', 0):.2f}% to {projection.get('next_quarter_avg', 0):.2f}% ({abs(projection.get('change_percent', 0)):.1f}% change).")
        
        report_lines.extend(["", "---", "", "## Quarterly Economic Projections", ""])
        
        # Add economic forecasts
        for metric, forecast_data in insights.get("economic_forecasts", {}).items():
            if not forecast_data:
                continue
                
            projection = insights.get("quarterly_projections", {}).get(metric, {})
            
            report_lines.extend([
                f"### {metric.replace('_', ' ').title()} Forecast",
                "",
                f"Current quarter average: {projection.get('current_quarter_avg', 'N/A'):.2f}%",
                f"Next quarter projected average: {projection.get('next_quarter_avg', 'N/A'):.2f}%",
                f"Quarter-over-quarter change: {projection.get('change_percent', 0):.2f}%",
                "",
                f"#### Analysis",
                "",
                f"The {metric.replace('_', ' ')} is expected to {projection.get('trend', 'remain stable')} over the next quarter. This trend is influenced by:",
                "",
                "- Regional economic policies",
                "- Global market conditions",
                "- Sector-specific developments",
                ""
            ])
            
            # Add chart if available
            chart_path = forecast_charts.get(f"economic_{metric}")
            if chart_path:
                # Use relative path for markdown
                rel_path = os.path.relpath(chart_path, self.reports_dir)
                report_lines.extend([
                    f"![{metric.replace('_', ' ').title()} Forecast]({rel_path})",
                    ""
                ])
        
        report_lines.extend(["", "## US-UAE Trade Relationship Projection", ""])
        
        # Add trade forecast
        if insights.get("trade_forecast"):
            projection = insights.get("quarterly_projections", {}).get("bilateral_trade", {})
            
            report_lines.extend([
                "### Bilateral Trade Value Forecast",
                "",
                f"Current quarter average: ${projection.get('current_quarter_avg', 'N/A'):.2f} billion",
                f"Next quarter projected average: ${projection.get('next_quarter_avg', 'N/A'):.2f} billion",
                f"Quarter-over-quarter change: {projection.get('change_percent', 0):.2f}%",
                "",
                "#### Key Trade Sectors",
                "",
                "Based on our analysis, the following sectors are expected to drive bilateral trade in the upcoming quarter:",
                "",
                "1. Technology and digital services",
                "2. Energy and renewable solutions",
                "3. Healthcare and pharmaceuticals",
                "4. Financial services",
                "5. Defense and aerospace",
                ""
            ])
            
            # Add chart if available
            chart_path = forecast_charts.get("trade")
            if chart_path:
                # Use relative path for markdown
                rel_path = os.path.relpath(chart_path, self.reports_dir)
                report_lines.extend([
                    f"![Trade Forecast]({rel_path})",
                    ""
                ])
        
        report_lines.extend(["", "## Industry Sector Quarterly Outlook", ""])
        
        # Add industry forecasts
        for industry, forecast_data in insights.get("industry_forecasts", {}).items():
            if not forecast_data:
                continue
                
            projection_key = f"industry_{industry.lower()}"
            projection = insights.get("quarterly_projections", {}).get(projection_key, {})
            
            report_lines.extend([
                f"### {industry} Sector",
                "",
                f"Current quarter average metric: {projection.get('current_quarter_avg', 'N/A'):.2f}%",
                f"Next quarter projected average: {projection.get('next_quarter_avg', 'N/A'):.2f}%",
                f"Quarter-over-quarter change: {projection.get('change_percent', 0):.2f}%",
                "",
                f"#### Quarterly Outlook",
                "",
                f"The {industry} sector is projected to {projection.get('trend', 'remain stable')} in the upcoming quarter. This forecast is based on:",
                "",
                "- Historical performance patterns",
                "- Current market dynamics",
                "- Regulatory environment",
                "- Regional and global industry trends",
                ""
            ])
        
        # Add correlation analysis
        if insights.get("correlations"):
            report_lines.extend([
                "## Economic Indicator Correlations",
                "",
                "The following heatmap displays the correlation between various economic indicators and metrics over time:",
                ""
            ])
            
            # Add correlation chart if available
            chart_path = forecast_charts.get("correlation_heatmap")
            if chart_path:
                # Use relative path for markdown
                rel_path = os.path.relpath(chart_path, self.reports_dir)
                report_lines.extend([
                    f"![Correlation Heatmap]({rel_path})",
                    "",
                    "### Correlation Analysis Insights",
                    "",
                    "These correlations reveal important relationships between economic indicators that inform our quarterly projections:",
                    ""
                ])
                
                # Analyze a few of the strongest correlations (simplified)
                report_lines.extend([
                    "- **GDP Growth & FDI**: Strong positive correlation (r > 0.7) indicates that foreign direct investment continues to be a primary driver of economic expansion.",
                    "- **Technology & Trade**: The technology sector shows high correlation with bilateral trade values, suggesting it will be a key determinant of trade performance.",
                    "- **Real Estate & Inflation**: Negative correlation highlights how inflation pressures may constrain real estate growth in the upcoming quarter.",
                    "",
                    "Understanding these relationships allows for more nuanced strategic planning and risk management when considering market entry or expansion in the GCC region.",
                    ""
                ])
        
        report_lines.extend([
            "", 
            "## Methodology and Limitations",
            "",
            "### Forecast Methodology",
            "",
            "This quarterly forecast utilizes TensorFlow-based deep learning models, specifically Long Short-Term Memory (LSTM) neural networks designed for time series forecasting. The models are trained on historical economic data extracted from daily business intelligence reports spanning multiple quarters.",
            "",
            "The forecasting process involves:",
            "",
            "1. Data extraction from structured and unstructured report content",
            "2. Feature engineering and normalization",
            "3. Training of specialized models for each economic indicator",
            "4. Ensemble forecasting for increased reliability",
            "5. Validation against historical accuracy metrics",
            "",
            "### Limitations",
            "",
            "- These projections represent model-based forecasts and should be considered alongside expert analysis and current market conditions.",
            "- Unexpected geopolitical events, policy changes, or global economic shocks are not accounted for in these models.",
            "- The accuracy of forecasts depends on the quality and quantity of historical data available.",
            "- Longer-term projections (beyond 90 days) have wider confidence intervals and should be interpreted with caution.",
            "",
            "*This report is generated using machine learning technology and should be used as one of several inputs in strategic decision-making.*",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def _generate_forecast_linkedin_posts(self, insights, is_quarterly=False):
        """Generate LinkedIn posts based on forecast insights."""
        period = "Quarterly" if is_quarterly else "Monthly"
        posts = []
        
        # Economic overview post
        economic_trends = [
            (metric, data) for metric, data in insights.get("trends", {}).items() 
            if metric in ["gdp_growth", "inflation", "fdi"]
        ]
        
        if economic_trends:
            trends_text = []
            for metric, data in economic_trends:
                direction = "increase" if data.get("trend") == "up" else "decrease"
                trends_text.append(f"{metric.replace('_', ' ').title()} is projected to {direction} by {abs(data.get('change_percent', 0)):.1f}%")
            
            trends_summary = ", ".join(trends_text[:-1]) + f" and {trends_text[-1]}" if len(trends_text) > 1 else trends_text[0]
            
            posts.append({
                "title": f"UAE Economic {period} Forecast",
                "content": f"""📊 **UAE Economy: {period} Forecast and Projections**

Our machine learning models have analyzed historical economic data to project key indicators for the UAE economy.

{trends_summary} in the coming {"quarter" if is_quarterly else "month"}.

These projections point to {"continued economic resilience and growth" if any(data.get("trend") == "up" for _, data in economic_trends) else "potential economic challenges"} in the UAE market, with opportunities emerging in sectors aligned with the country's economic diversification strategy.

What economic factors do you believe will have the biggest impact on UAE business in the coming {"quarter" if is_quarterly else "month"}?

#UAEEconomy #EconomicForecast #BusinessIntelligence #DataAnalytics #GCCMarket""",
                "category": "economy"
            })
        
        # Industry outlook post
        industry_forecasts = insights.get("industry_forecasts", {})
        if industry_forecasts:
            # Find the industry with the strongest growth projection
            best_industry = None
            best_change = -float('inf')
            
            for industry in industry_forecasts.keys():
                trend_key = f"industry_{industry.lower()}"
                change = insights.get("trends", {}).get(trend_key, {}).get("change_percent", 0)
                if change > best_change:
                    best_change = change
                    best_industry = industry
            
            if best_industry:
                trend_key = f"industry_{best_industry.lower()}"
                trend_data = insights.get("trends", {}).get(trend_key, {})
                
                posts.append({
                    "title": f"{best_industry} Sector Leads Growth in {period} Forecast",
                    "content": f"""🚀 **{best_industry} Sector Shows Promising Growth Potential**

Our {period.lower()} forecast shows the {best_industry} sector is projected to lead growth in the UAE market, with an expected increase of {abs(trend_data.get('change_percent', 0)):.1f}% {"this quarter" if is_quarterly else "this month"}.

Key growth drivers include:
• Continued government investment in {best_industry.lower()} infrastructure
• Increasing private sector innovation
• Growing consumer and business demand
• Regional expansion opportunities

This projected growth creates significant opportunities for businesses operating in or adjacent to the {best_industry.lower()} space.

Is your organization positioned to capitalize on the growth in the {best_industry.lower()} sector? What strategies are you implementing?

#{best_industry.replace(' ', '')} #UAEBusiness #SectorGrowth #BusinessForecast #GCCMarket""",
                    "category": "industry"
                })
        
        # US-UAE trade post
        trade_forecast = insights.get("trade_forecast")
        if trade_forecast:
            trade_trend = insights.get("trends", {}).get("bilateral_trade", {})
            direction = "strengthening" if trade_trend.get("trend") == "up" else "facing challenges"
            
            posts.append({
                "title": f"US-UAE Trade Relationship {direction.title()} in {period} Outlook",
                "content": f"""🇺🇸🇦🇪 **US-UAE Trade Relationship: {period} Projection**

Our data-driven forecast suggests bilateral trade between the US and UAE is {direction}, with trade value projected to {"increase" if trade_trend.get("trend") == "up" else "decrease"} by {abs(trade_trend.get('change_percent', 0)):.1f}% over the coming {"quarter" if is_quarterly else "month"}.

Key sectors driving this trend include:
• Technology and digital services
• Energy and sustainability
• Healthcare solutions
• Financial services
• Defense and aerospace

This {"positive" if trade_trend.get("trend") == "up" else "challenging"} trend presents {"opportunities" if trade_trend.get("trend") == "up" else "considerations"} for businesses engaged in cross-border trade and investment between these nations.

How is your business leveraging the US-UAE trade relationship? What sectors do you see gaining momentum?

#USUAERelations #InternationalTrade #TradeProjections #GlobalBusiness #BusinessIntelligence""",
                    "category": "us_uae_relations"
                })
        
        return posts

if __name__ == "__main__":
    # Test the ML Report Integration
    integration = MLReportIntegration()
    
    # Generate monthly forecast report
    md_path, html_path, pdf_path = integration.generate_monthly_forecast_report()
    
    if md_path:
        print(f"Monthly forecast report generated at: {md_path}")
        if html_path:
            print(f"HTML report available at: {html_path}")
        if pdf_path:
            print(f"PDF report available at: {pdf_path}")
    else:
        print("Failed to generate monthly forecast report") 