module.exports = {
  apps: [{
    name: 'teleglas-gpt-api',
    script: 'gpt_api_main.py',
    interpreter: '/home/ubuntu/TELEGLAS/gpt_api/venv/bin/python',
    cwd: '/home/ubuntu/TELEGLAS/gpt_api',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/home/ubuntu/TELEGLAS'
    },
    env_production: {
      NODE_ENV: 'production',
      GPT_API_DEBUG: 'false',
      GPT_API_ENVIRONMENT: 'production'
    },
    env_development: {
      NODE_ENV: 'development',
      GPT_API_DEBUG: 'true',
      GPT_API_ENVIRONMENT: 'development'
    },
    error_file: 'logs/pm2-error.log',
    out_file: 'logs/pm2-out.log',
    log_file: 'logs/pm2-combined.log',
    time: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 4000,
    
    // Health check configuration
    health_check_grace_period: 3000,
    health_check_fatal_exceptions: true,
    
    // Process monitoring
    pmx: true,
    
    // Custom configuration for API
    kill_timeout: 5000,
    listen_timeout: 3000,
    
    // Resource limits
    max_cpu_restart: '80%',
    
    // Logging configuration
    output: './logs/pm2-out.log',
    error: './logs/pm2-error.log',
    log: './logs/pm2-combined.log',
    
    // Advanced configuration
    node_args: [
      '--max-old-space-size=1024'
    ],
    
    // Instance variables
    instance_var: 'INSTANCE_ID',
    
    // Cron jobs (optional)
    cron_restart: '0 2 * * *',  // Restart daily at 2 AM
    
    // Environment-specific settings
    // Production settings are applied when NODE_ENV=production
    // Development settings are applied when NODE_ENV=development
  }]
};
