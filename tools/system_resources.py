import psutil
import os

def run_system_resources():
    print("="*60)
    print("            MONITOR DE RECURSOS DE HARDWARE            ")
    print("="*60)
    
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    
    print(f"CPU Total Uso: {cpu}%")
    print(f"RAM Total: {mem.total / (1024**3):.1f} GB")
    print(f"RAM Usada: {mem.used / (1024**3):.1f} GB ({mem.percent}%)")
    print(f"RAM Livre: {mem.available / (1024**3):.1f} GB")
    
    print("-" * 60)
    print("Processos Relevantes:")
    
    mt5_mem = 0
    bot_mem = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            name = proc.info['name'].lower()
            if 'terminal64.exe' in name or 'metatrader' in name:
                mt5_mem += proc.info['memory_info'].rss
            elif 'python' in name:
                bot_mem += proc.info['memory_info'].rss
        except:
            pass
            
    print(f"MetaTrader 5: {mt5_mem / (1024**2):.1f} MB")
    print(f"Processos Python: {bot_mem / (1024**2):.1f} MB")
    
    if mem.available < 500 * 1024 * 1024:
        print("\nALERTA: RAM Livre critica (menos de 500MB). Cuidado com ML e XGBoost!")
        
    print("="*60)

if __name__ == "__main__":
    run_system_resources()
