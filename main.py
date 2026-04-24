import tkinter as tk
import tkinter.filedialog as filedialog
from multi_LIV import multi_LIV
from multi_osa import multi_OSA
from multi_wlm  import multi_WLM
import multi_select
import tkinter.simpledialog as simpledialog
#if this doesnt work try removing it try opening in powershell with following command:
# PS H:\> cd 'C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration'
#PS C:\Users\jsheri1\Documents\GitHub\Wafer-Scale-Laser-Integration> python main.py

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Ask for the parent directory and select subfolders
    parent_dir = filedialog.askdirectory(title="Select Parent Directory for Data Processing")
    file_selection = multi_select.scrape_filenames(root, parent_dir)  # Open the selection GUI

    # Ask if the user wants to overwrite existing files
    overwrite_existing = tk.messagebox.askyesno("Overwrite Existing Files", "Do you want to overwrite existing files?")

    print(f"Selected files: {file_selection}")
    
    # Ask the user which analysis to run
    def ask_analysis_type(parent):
        print("\n" + "="*60)
        print("IMPORTANT: A dialog window is about to appear!")
        print("Please check your taskbar or alt-tab if you don't see it.")
        print("="*60 + "\n")
        
        # Ensure parent is visible and on top so dialog appears
        try:
            parent.deiconify()
            parent.lift()
            parent.focus_force()
            parent.attributes('-topmost', True)
            parent.update()
        except Exception:
            pass

        dialog = tk.Toplevel(parent)
        dialog.title('Select analysis type')
        dialog.transient(parent)
        
        # Make dialog visible and on top - more aggressive settings
        dialog.attributes('-topmost', True)
        dialog.lift()
        dialog.focus_force()
        dialog.update()
        
        # Make it bigger and more noticeable
        dialog.minsize(300, 200)
        
        dialog.grab_set()

        var = tk.StringVar(value='LIV')

        tk.Label(dialog, text='Which analysis would you like to run?').pack(padx=12, pady=(12, 4))
        rb_frame = tk.Frame(dialog)
        rb_frame.pack(padx=12, pady=4)
        tk.Radiobutton(rb_frame, text='LIV', variable=var, value='LIV').pack(anchor='w')
        tk.Radiobutton(rb_frame, text='OSA', variable=var, value='OSA').pack(anchor='w')
        tk.Radiobutton(rb_frame, text='WLM', variable=var, value='WLM').pack(anchor='w')

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(padx=12, pady=(8, 12))

        def on_ok():
            dialog.selected = var.get()
            dialog.destroy()

        def on_cancel():
            dialog.selected = None
            dialog.destroy()

        tk.Button(btn_frame, text='OK', width=10, command=on_ok).pack(side='left', padx=6)
        tk.Button(btn_frame, text='Cancel', width=10, command=on_cancel).pack(side='left')

        # Center the dialog on screen
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')
        
        # Add a timeout - if dialog isn't interacted with in 5 seconds, print a reminder
        def reminder():
            if dialog.winfo_exists():
                print("\n>>> The analysis selection dialog is waiting for your input! <<<")
                print(">>> Check your taskbar or press Alt+Tab to find it <<<\n")
                dialog.after(5000, reminder)  # Remind again in 5 seconds
        
        dialog.after(5000, reminder)  # First reminder after 5 seconds

        parent.wait_window(dialog)
        selected = getattr(dialog, 'selected', None)
        
        # Console fallback if dialog was cancelled or didn't show
        if not selected:
            print('\n' + '='*60)
            print('Analysis Selection Dialog')
            print('='*60)
            print('No GUI selection detected. Please select analysis type:')
            print('  1) LIV')
            print('  2) OSA')
            print('  3) WLM')
            print('  (or press Enter to cancel)')
            try:
                choice = input('Enter choice (1, 2, 3, LIV, OSA, WLM): ')
                choice = choice.strip().upper()
                if choice in ('1', 'LIV'):
                    return 'LIV'
                elif choice in ('2', 'OSA'):
                    return 'OSA'
                elif choice in ('3', 'WLM'):
                    return 'WLM'
            except Exception:
                pass
            return None
        
        return selected

    analysis = ask_analysis_type(root)
    print(f"User selected analysis: {analysis}")
    if analysis == 'LIV':
        print("Processing LIV files...")
        multi_liv = multi_LIV(parent_dir, selected_files=file_selection, overwrite_existing=overwrite_existing)
        multi_liv.plot_beeswarm_by_wavelength(interactive_li=False)
    elif analysis == 'OSA':
        print("Processing OSA files...")
        multi_osa = multi_OSA(parent_dir, selected_files=file_selection, overwrite_existing=overwrite_existing)
    elif analysis == 'WLM':
        print("Processing WLM files...")
        multi_wlm = multi_WLM(parent_dir, selected_files=file_selection, overwrite_existing=overwrite_existing)
    else:
        print('No analysis selected — exiting')

    root.destroy()