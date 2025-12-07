
from speedhive_tools import Speedhive

# Replace with a known session ID (from one of the events you printed earlier)
SESSION_ID = 10802278  # TODO: put a real one here

def main():
    sh = Speedhive()

    # Classification
    try:
        cls = sh.session_classification(SESSION_ID)
        print("Classification keys:", list(cls.keys())[:10] if isinstance(cls, dict) else type(cls))
    except Exception as e:
        print("Classification error:", e)

    # Lap chart
    try:
        chart = sh.session_lapchart(SESSION_ID)
        print("Lap chart keys:", list(chart.keys())[:10] if isinstance(chart, dict) else type(chart))
    except Exception as e:
        print("Lap chart error:", e)

if __name__ == "__main__":
    main()
