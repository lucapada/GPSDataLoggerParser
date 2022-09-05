import os
d = os.path.dirname(os.path.abspath(__file__)).replace("\\","/") + "/rtklib_2.4.2/bin"
print(os.chdir(d))
print(os.getcwd())