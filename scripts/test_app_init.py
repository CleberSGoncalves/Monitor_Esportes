import sys
sys.path.insert(0, ".")

try:
    from gui.main_gui import MonitorApp
    print("Imported MonitorApp successfully.")
    
    app = MonitorApp()
    print("MonitorApp() instantiated successfully!")
    print(f"events_box exists: {hasattr(app, 'events_box')}")
    print(f"cbf_ticker_frame exists: {hasattr(app, 'cbf_ticker_frame')}")
    print(f"monitoring_mode: {app.monitoring_mode_var.get()}")
    
    app.destroy()
    print("App destroyed cleanly. TEST PASSED 100%!")
    sys.exit(0)
except Exception as e:
    import traceback
    print("FAILED TO INITIALIZE:")
    traceback.print_exc()
    sys.exit(1)
