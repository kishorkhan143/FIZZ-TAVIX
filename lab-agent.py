import psutil
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. CONFIGURATION (UPDATE YOUR DETAILS HERE)
# ==========================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "kishorkhan.dev@gmail.com"       # Your Gmail address
SENDER_PASSWORD = "rinv jjhh yxnh hyas"   # Your 16-character Gmail App Password inside quotes
INCHARGE_EMAIL = "latheefkhan1212@gmail.com" # Lab Incharge Email

reported_connections = set()

def send_ssh_email_alert(remote_ip, remote_port):
    subject = f"🚨 SECURITY ALERT: Unauthorized SSH Connection to {remote_ip}"
    
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px; border: 2px solid #c0392b; border-radius: 8px;">
        <h2 style="color: #c0392b;">⚠️ Active SSH Connection Detected</h2>
        <p>A computer in the lab has established an outbound SSH session.</p>
        <ul>
          <li><strong>Destination IP:</strong> <code>{remote_ip}</code></li>
          <li><strong>Destination Port:</strong> <code>{remote_port}</code> (SSH)</li>
          <li><strong>Timestamp:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</li>
        </ul>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = INCHARGE_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        print(f"Connecting to SMTP server ({SMTP_SERVER})...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, INCHARGE_EMAIL, msg.as_string())
        server.quit()
        print(f" SUCCESS! Email alert sent to {INCHARGE_EMAIL}!")
    except Exception as e:
        print(f" FAILED TO SEND EMAIL: {e}")

# ==========================================
# 2. REAL-TIME MONITORING LOOP
# ==========================================
print("🔍 Tavix-Guard Lab Agent running... Monitoring Port 22 (SSH)...")

while True:
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED' and conn.raddr:
                remote_ip, remote_port = conn.raddr.ip, conn.raddr.port
                
                if remote_port == 22 and remote_ip not in reported_connections:
                    print(f"\n🚨 SSH CONNECTION DETECTED -> {remote_ip}:{remote_port}")
                    send_ssh_email_alert(remote_ip, remote_port)
                    reported_connections.add(remote_ip)
                    
    except Exception as e:
        print(f"Error checking connections: {e}")
        
    time.sleep(1)