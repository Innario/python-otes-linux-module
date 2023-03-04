import subprocess
from collections import Counter
import time

ps = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE, encoding="utf8").stdout.readlines()
columns = ps[0].strip().split(None)
data = {column: [] for column in columns}
print(columns)
for row in ps[1:]:
    cells = row.split()
    for i, column in enumerate(columns[:-1]):
        data[column].append(cells[i])
    # if len(cells) > 11:
    #     print(" ".join(cells))
    data[columns[-1]].append(" ".join(cells[i+1:]))

id = list(range(len(data["USER"])))
id_mem_max = sorted(id, key=lambda i: float(data["%MEM"][i]))[-1]
id_cpu_max = sorted(id, key=lambda i: float(data["%CPU"][i]))[-1]
timestamp = time.strftime("%Y-%m-%d %X")

report = f"""
System report {timestamp}
- system users: {set(data["USER"])}
- number of processes: {len(data["USER"])}
- number of processes per user: {dict(Counter(data["USER"]))}
- total memory usage: {sum(float(mem) for mem in data["%MEM"]) * 8 * 1024 / 100:.1f} Mb
- total cpu usage: {sum(float(cpu) for cpu in data["%CPU"]):.1f} %
- max memory use: {data["%MEM"][id_mem_max]}% by {data["COMMAND"][id_mem_max][:20]}
- max cpu use: {data["%CPU"][id_cpu_max]}% by {data["COMMAND"][id_cpu_max][:20]}
"""

print(report)
with open(f"{timestamp} report.txt", "w") as file:
    file.write(report)
