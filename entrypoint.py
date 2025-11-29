import subprocess

# Ensure all modules load before Streamlit execution
import main  # This ensures all module loads happen before Streamlit execution

if __name__ == "__main__":
    # Use subprocess to run the Streamlit app
    subprocess.run(["streamlit", "run", "main.py"])
