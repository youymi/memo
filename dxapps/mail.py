import smtplib  
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText  
from email.mime.image import MIMEImage  
  
sender = 'youynu@163.com'
receiver = 'youymi@163.com'
subject = 'mysql_bak'
smtpserver = 'smtp.163.com'  
username = 'youynu@163.com'
password = '122011846'
  
msgRoot = MIMEMultipart('alternative')
msgRoot['Subject'] = 'Mysql backup data'

text = "Hi,Let's go this week?"
msgRoot.attach(MIMEText(text, 'plain'))
#构造附件  
att = MIMEText(open('d:\\data\\sh\\back_mysql.sh', 'rb').read(), 'base64', 'utf-8')
#att = MIMEText(open('d:\\1.rar', 'rb').read(), 'base64', 'utf-8')
att["Content-Type"] = 'application/octet-stream'  
att["Content-Disposition"] = 'attachment; filename="1.sh"'
msgRoot.attach(att)  
          
smtp = smtplib.SMTP()  
smtp.connect(smtpserver)
smtp.login(username, password)  
smtp.sendmail(sender, receiver, msgRoot.as_string())  
smtp.quit()