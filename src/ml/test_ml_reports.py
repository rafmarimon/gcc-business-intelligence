#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime

# Setup base path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
try:
    from ml.report_integration import MLReportIntegration
except ImportError:
    print("Error importing MLReportIntegration. Make sure paths are correct.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ml_test')

def generate_test_data(test_dir):
    """Generate some test report data for demonstration purposes."""
    logger.info("Generating test reports for ML analysis")
    
    # Create test directory if it doesn't exist
    os.makedirs(test_dir, exist_ok=True)
    
    # Generate some sample reports with economic data patterns
    for month in range(1, 7):  # Generate 6 months of test data
        for day in [1, 8, 15, 22]:  # Weekly reports
            # Create timestamp
            report_date = datetime(2025, month, day)
            timestamp = report_date.strftime("%Y%m%d_%H%M%S")
            
            # Simulate some trending economic data
            # GDP growth: starting at 3.2% and increasing slightly each month
            gdp_growth = 3.2 + (month * 0.1)
            
            # Inflation: starting at 2.5% and decreasing slightly
            inflation = 2.5 - (month * 0.05)
            
            # FDI: increasing steadily
            fdi = 12 + (month * 0.8)
            
            # Create a test report with the data
            report_path = os.path.join(test_dir, f"consolidated_report_{timestamp}.md")
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"# Business Intelligence Report: {report_date.strftime('%B %d, %Y')}\n\n")
                f.write(f"**Generated:** {report_date.strftime('%B %d, %Y')} | **Report ID:** {timestamp}\n\n")
                f.write("## Economic Insights\n\n")
                f.write("The UAE economy continues to show resilience despite global challenges.\n\n")
                f.write("### Key Economic Indicators\n")
                f.write(f"- GDP Growth: {gdp_growth:.1f}%\n")
                f.write(f"- Inflation: {inflation:.1f}%\n")
                f.write(f"- Foreign Direct Investment: Increased by {fdi:.1f}% year-over-year\n\n")
                
                # Add industry data
                f.write("## Industry Developments\n\n")
                
                # Technology sector - strong growth
                tech_growth = 8.0 + (month * 0.5)
                f.write("### Technology\n")
                f.write(f"The technology sector has increased by {tech_growth:.1f}% in the last quarter, showing strong market activity.\n\n")
                
                # Real Estate - moderate growth
                real_estate_growth = 4.0 + (month * 0.3)
                f.write("### Real Estate\n")
                f.write(f"Property transactions in Dubai increased by {real_estate_growth:.1f}% in the last quarter.\n\n")
                
                # Energy - fluctuating
                energy_growth = 5.0 + (month * 0.2) - (month % 2 * 0.5)
                f.write("### Energy\n")
                f.write(f"The energy sector saw a {energy_growth:.1f}% change in activity.\n\n")
                
                # US-UAE Trade data
                trade_value = 22.0 + (month * 0.5)
                f.write("## US-UAE Relations\n\n")
                f.write(f"Bilateral trade between the US and UAE reached ${trade_value:.1f} billion in the past year.\n\n")
                
                # Add a footer
                f.write("---\n\n")
                f.write(f"*© Test Data. Report generated for ML testing on {report_date.strftime('%B %d, %Y')}.*\n")
    
    logger.info(f"Generated {6 * 4} test reports in {test_dir}")
    return test_dir

def main():
    """Run the ML report test."""
    print("=" * 80)
    print("TESTING ML REPORT GENERATION")
    print("=" * 80)
    print("\nThis script will:")
    print("1. Generate sample test data with economic patterns")
    print("2. Use TensorFlow to analyze data and identify trends")
    print("3. Generate monthly and quarterly forecasts using ML")
    print("\n" + "=" * 80 + "\n")
    
    # Create a test directory
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_reports")
    
    # Generate test data
    generate_test_data(test_dir)
    
    # Initialize the ML Report Integration with the test directory
    integration = MLReportIntegration(reports_dir=test_dir)
    
    print("\nGenerating monthly forecast report...")
    # Generate monthly forecast report
    md_path, html_path, pdf_path = integration.generate_monthly_forecast_report()
    
    if md_path:
        print(f"\n✅ Success! Monthly forecast report generated:")
        print(f"  • Markdown: {md_path}")
        if html_path:
            print(f"  • HTML: {html_path}")
        if pdf_path:
            print(f"  • PDF: {pdf_path}")
            
        print("\nTo view the HTML report, open it in your browser:")
        print(f"open {html_path}")
    else:
        print("\n❌ Failed to generate monthly forecast report")
    
    print("\nGenerating quarterly forecast report...")
    # Generate quarterly forecast report
    md_path, html_path, pdf_path = integration.generate_quarterly_forecast_report()
    
    if md_path:
        print(f"\n✅ Success! Quarterly forecast report generated:")
        print(f"  • Markdown: {md_path}")
        if html_path:
            print(f"  • HTML: {html_path}")
        if pdf_path:
            print(f"  • PDF: {pdf_path}")
            
        print("\nTo view the HTML report, open it in your browser:")
        print(f"open {html_path}")
    else:
        print("\n❌ Failed to generate quarterly forecast report")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main() 