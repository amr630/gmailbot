import subprocess
import sys

# تشغيل بوت العملاء وبوت الأدمن معاً في نفس الوقت
process1 = subprocess.Popen([sys.executable, "user_bot.py"])
process2 = subprocess.Popen([sys.executable, "admin_bot.py"])

# إبقاء السكربت يعمل باستمرار
process1.wait()
process2.wait()