module.exports = {
  apps: [
    {
      name: 'dinepixel-api',
      script: '.venv/bin/uvicorn',
      args: 'main:app --host 127.0.0.1 --port 8000 --workers 2',
      cwd: '/home/deploy/dinepixel-api',
      interpreter: 'none',
      env: {
        PATH: '/home/deploy/dinepixel-api/.venv/bin:' + process.env.PATH,
      },
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      out_file: '/home/deploy/.pm2/logs/dinepixel-api-out.log',
      error_file: '/home/deploy/.pm2/logs/dinepixel-api-error.log',
      time: true,
    },
  ],
};
