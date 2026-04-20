import pandas as pd
import matplotlib.pyplot as plt

# csv_file="testing_results/snmp_2026-03-23.csv"
# csv_file = "snmp_2026-04-05.csv"
csv_file="Results/Apr-2026/04-18-2026_14_18.csv"
channel=[3,4,5,6,7]
parsemethod = 3 
# def plotLog(csv_file, channel=0):
if 1:
    df = pd.read_csv(csv_file)
    df["time"] = pd.to_datetime(df["time"])
    if type[channel] == type(0):
        channel = [channel]

    fig, (ax1,ax2) = plt.subplots(2,1)
    
    
    for n,ch in enumerate(channel):
        if parsemethod<3:
            d = df[df["Ch"] == ch]

            # convert numeric
            d["V"] = pd.to_numeric(df["V"])
            d["I"] = pd.to_numeric(df["I"])

            ax1.plot(d["time"], d[f"V"], '.-', label=f"Ch {ch}")
            ax2.plot(d["time"], d["I"], ".-", label=f"Ch {ch}")
        else:
            # convert numeric
            df[f"V{ch}"] = pd.to_numeric(df[f"V{ch}"])
            df[f"I{ch}"] = pd.to_numeric(df[f"I{ch}"])

            ax1.plot(df["time"], df[f"V{ch}"], '.-', label=f"Ch {ch}")
            ax2.plot(df["time"], df[f"I{ch}"], ".-", label=f"Ch {ch}")
        
    ax1.set_ylabel("Voltage (V)")
    ax2.set_ylabel("Current (A)")
    fig.suptitle(f"Ch {channel}")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend(fontsize='x-small')
    plt.show()
    plt.savefig(f"{csv_file[:-4]}.png", dpi=150)



# plotLog("snmp_2026-03-23.csv",channel=2)
# 