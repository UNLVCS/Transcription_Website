# 🚀 Deployment Checklist

Use this checklist to ensure a smooth deployment to your production server.

## ✅ Pre-Deployment Checklist

### System Requirements
- [ ] Ubuntu 20.04+ or similar Linux OS
- [ ] Python 3.9+ installed
- [ ] PostgreSQL 12+ installed and running
- [ ] ffmpeg installed
- [ ] At least 50GB free disk space
- [ ] At least 8GB RAM (16GB recommended)
- [ ] (Optional) NVIDIA GPU with CUDA for faster processing

### Security
- [ ] Changed `SECRET_KEY` in `.env` to a random value
- [ ] Updated PostgreSQL password to a strong password
- [ ] Set up firewall (UFW or iptables)
- [ ] Configured SSH key-based authentication (disable password login)
- [ ] Set up regular backups for database and files

### Database Setup
- [ ] PostgreSQL service is running
- [ ] Database `meeting_minutes` created
- [ ] Database user created with appropriate permissions
- [ ] Database connection tested successfully
- [ ] Database initialized with tables

### Application Setup
- [ ] All files uploaded to `/var/www/meeting_minutes`
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] `.env` file configured correctly
- [ ] Directory permissions set correctly
- [ ] Test run completed successfully

## 📋 Deployment Steps (Quick Reference)

### 1. Initial Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3.9 python3.9-venv python3-pip postgresql postgresql-contrib ffmpeg -y

# Create application directory
sudo mkdir -p /var/www/meeting_minutes
cd /var/www/meeting_minutes
```

### 2. Database Setup
```bash
# Login to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE meeting_minutes;
CREATE USER meeting_user WITH PASSWORD 'STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON DATABASE meeting_minutes TO meeting_user;
\q
```

### 3. Application Setup
```bash
# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your values

# Initialize database
python3 -c "from app import init_db; init_db()"
```

### 4. Production Deployment (Choose One)

#### Option A: Systemd Service (Recommended)
```bash
# Copy service file
sudo cp meeting-minutes.service /etc/systemd/system/
sudo nano /etc/systemd/system/meeting-minutes.service  # Update YOUR_USERNAME

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable meeting-minutes
sudo systemctl start meeting-minutes
sudo systemctl status meeting-minutes
```

#### Option B: Screen Session (Simple)
```bash
screen -S meeting-minutes
cd /var/www/meeting_minutes
source venv/bin/activate
gunicorn --workers 4 --threads 2 --timeout 7200 --bind 0.0.0.0:5000 app:app
# Press Ctrl+A then D to detach
```

### 5. Nginx Setup (Recommended)
```bash
# Install nginx
sudo apt install nginx -y

# Copy configuration
sudo cp nginx.conf /etc/nginx/sites-available/meeting-minutes
sudo nano /etc/nginx/sites-available/meeting-minutes  # Update your-domain.com

# Enable site
sudo ln -s /etc/nginx/sites-available/meeting-minutes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Setup Cron Job for Cleanup
```bash
crontab -e
# Add: 0 2 * * * curl http://localhost:5000/api/cleanup
```

## ✅ Post-Deployment Checklist

### Testing
- [ ] Application is accessible via web browser
- [ ] Can create a user account
- [ ] Can login successfully
- [ ] Upload form accepts files
- [ ] Can upload a small test audio file (1-2 minutes)
- [ ] Job status page updates in real-time
- [ ] Processing completes successfully
- [ ] Can download transcript and minutes
- [ ] Files are auto-deleted after 30 days (test with old data)

### Monitoring
- [ ] Application logs are accessible
- [ ] Database is accessible
- [ ] Disk space is monitored
- [ ] Set up alerts for errors (optional)
- [ ] Documented how to check logs

### Security
- [ ] Firewall is active and configured
- [ ] Only necessary ports are open (22, 80, 443)
- [ ] SSL/HTTPS is configured (recommended)
- [ ] Regular backups are scheduled
- [ ] Backup restoration tested

### Documentation
- [ ] README.md accessible to team
- [ ] USER_GUIDE.md shared with users
- [ ] API key setup instructions shared
- [ ] Admin contact information documented

## 🔧 Verification Commands

Run these to verify everything is working:

```bash
# Check service status
sudo systemctl status meeting-minutes

# Check application logs
sudo journalctl -u meeting-minutes -f

# Check PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT COUNT(*) FROM jobs;" meeting_minutes

# Check disk space
df -h

# Check nginx
sudo nginx -t
sudo systemctl status nginx

# Test database connection
psql -U meeting_user -d meeting_minutes -h localhost -c "SELECT 1;"

# Check if port is listening
sudo netstat -tulpn | grep 5000
```

## 🎯 Performance Tuning

### For High-Volume Usage
```bash
# Increase worker processes in systemd service
# Change: --workers 4 to --workers 8

# Optimize PostgreSQL
sudo -u postgres psql
ALTER DATABASE meeting_minutes SET work_mem = '256MB';
ALTER DATABASE meeting_minutes SET maintenance_work_mem = '512MB';
```

### For GPU Servers
```bash
# Set specific GPU
export CUDA_VISIBLE_DEVICES=0

# Or in systemd service file:
Environment="CUDA_VISIBLE_DEVICES=0"
```

## 🆘 Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Can't connect to database | Check PostgreSQL running, verify .env credentials |
| Port 5000 in use | `sudo lsof -i :5000` and kill process |
| Permission denied | `sudo chown -R $USER:$USER /var/www/meeting_minutes` |
| CUDA out of memory | Reduce batch_size in app.py or use CPU |
| Upload fails | Check client_max_body_size in nginx.conf |
| Processing stalls | Check logs, restart service |

## 📊 Monitoring Dashboard (Optional)

Set up basic monitoring:

```bash
# Create monitoring script
cat > /var/www/meeting_minutes/monitor.sh << 'EOF'
#!/bin/bash
echo "=== Meeting Minutes Status ==="
echo "Service: $(systemctl is-active meeting-minutes)"
echo "Database: $(systemctl is-active postgresql)"
echo "Jobs in DB: $(sudo -u postgres psql -t -c 'SELECT COUNT(*) FROM jobs;' meeting_minutes)"
echo "Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"
echo "Memory: $(free -h | awk 'NR==2 {print $3 " / " $2}')"
EOF

chmod +x /var/www/meeting_minutes/monitor.sh

# Run it
./monitor.sh
```

## 🎉 Success Criteria

Your deployment is successful when:
- ✅ Users can access the website
- ✅ Users can upload audio files
- ✅ Processing completes without errors
- ✅ Transcripts and minutes are generated correctly
- ✅ System is stable for 24+ hours
- ✅ Automatic cleanup works
- ✅ Backups are running

## 📞 Support Resources

- **System Logs**: `/var/log/syslog`
- **Application Logs**: `sudo journalctl -u meeting-minutes`
- **PostgreSQL Logs**: `/var/log/postgresql/`
- **Nginx Logs**: `/var/log/nginx/`

## 🔄 Regular Maintenance

### Weekly
- [ ] Check disk space
- [ ] Review application logs for errors
- [ ] Verify backups completed

### Monthly
- [ ] Update system packages: `sudo apt update && sudo apt upgrade`
- [ ] Review and optimize database
- [ ] Test backup restoration
- [ ] Review user feedback

### Quarterly
- [ ] Update Python dependencies: `pip install --upgrade -r requirements.txt`
- [ ] Review and update documentation
- [ ] Audit security settings
- [ ] Performance optimization review

---

**Congratulations on your deployment! 🎉**

For questions or issues, refer to README.md and USER_GUIDE.md
