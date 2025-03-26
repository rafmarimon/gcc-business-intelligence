# GCC Business Intelligence Platform - Deployment Guide

This guide provides instructions for deploying the GCC Business Intelligence Platform to Digital Ocean's App Platform.

## Prerequisites

1. A Digital Ocean account with App Platform access
2. GitHub repository containing the project code
3. Digital Ocean CLI (optional)

## Deployment Steps

### 1. Prepare Your Code

Ensure your code is properly set up for deployment:

1. Verify that `requirements.txt` includes all necessary dependencies, including gunicorn
2. Make sure the `.do/app.yaml` file is present and properly configured
3. Update the repository information in the `.do/app.yaml` file:
   ```yaml
   github:
     repo: your-username/your-repo-name  # Replace with your actual GitHub repo
     branch: main  # Replace with your deployment branch
   ```

### 2. Deploy Using Digital Ocean Dashboard

1. Log in to your Digital Ocean account
2. Go to "Apps" in the left navigation menu
3. Click "Create App"
4. Select your GitHub repository and branch
5. Digital Ocean will automatically detect your app.yaml configuration
6. Review the settings and click "Create Resources"
7. Wait for the deployment to complete

### 3. Deploy Using Digital Ocean CLI (Alternative)

If you have the Digital Ocean CLI installed, you can deploy with:

```bash
doctl apps create --spec .do/app.yaml
```

To update an existing app:

```bash
doctl apps update [APP_ID] --spec .do/app.yaml
```

## Post-Deployment Configuration

After deployment, you may need to:

1. Configure environment variables in the Digital Ocean dashboard
2. Set up proper domain routing if using a custom domain
3. Enable SSL/TLS for secure connections

## Monitoring and Logs

Monitor your application:

1. In the Digital Ocean dashboard, go to your app
2. Select the "Insights" tab for performance metrics
3. View logs by clicking on the component and selecting "Logs"

## Troubleshooting

Common issues:

1. **Application fails to start**: Check logs for errors. Verify that the `run_command` in app.yaml is correct.
2. **Missing dependencies**: Make sure all dependencies are listed in requirements.txt.
3. **Template not found**: Ensure paths in the Flask app are correct relative to the deployment environment.

## Structure for Digital Ocean Deployment

The application is structured as follows for Digital Ocean:

- `src/deployments/digital_ocean_app.py`: The main application file that Gunicorn will run
- `.do/app.yaml`: Digital Ocean App Platform configuration
- `requirements.txt`: Dependencies including gunicorn

## Additional Resources

- [Digital Ocean App Platform Documentation](https://docs.digitalocean.com/products/app-platform/)
- [Gunicorn Documentation](https://docs.gunicorn.org/en/stable/)
- [Flask Deployment Options](https://flask.palletsprojects.com/en/2.3.x/deploying/) 