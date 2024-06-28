import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DateGenerator:
    def __init__(self, args):
        self.args = args 

    def __del__(self):
        pass 

    def generate_dates_with_intervals(self, days=None):
        if self.args is not None:
            # Define the number of intervals per day
            if self.args.model_interval == "1m":
                interval_minutes = 1
            elif self.args.model_interval == "2m":
                interval_minutes = 2
            elif self.args.model_interval == "5m":
                interval_minutes = 5
            elif self.args.model_interval == "15m":
                interval_minutes = 15
            elif self.args.model_interval == "30m":
                interval_minutes = 30
            elif self.args.model_interval == "60m":
                interval_minutes = 60 
            elif self.args.model_interval == "90m":
                interval_minutes = 90
            elif self.args.model_interval == "1h":
                interval_minutes = 60 
            elif self.args.model_interval == "1d":
                interval_minutes = 24*60 
            elif self.args.model_interval == "5d":
                interval_minutes = 24*60*5 
            elif self.args.model_interval == "1w":
                interval_minutes = 24*60*7
            elif self.args.model_interval == "1mo":
                interval_minutes = 24*60*30 # assumes 30 days in a month may cause issues 
            elif self.args.model_interval == "3mo":
                interval_minutes = 24*60*30*3 # assumes 30 days in a month and that 3 months is 90 days 
            else:
                logger.error(f"Interval Minutes could not be set by Model Interval {self.args.model_interval}. Applying interval of 1m.")
                interval_minutes = 1

        else:
            interval_minutes = 1
        
        # Create a list to store all dates and times
        dates = self.generate_datetime_list(sim_time=self.args.sim_time, interval_minutes=interval_minutes)
        
        return dates

    def generate_datetime_list(self, sim_time=None, interval_minutes=None, days=None):
        dates = []
        intervals_per_day = int(24 * 60 / interval_minutes)
        
        if sim_time is not None:
            for day in range(sim_time):
                start_of_day = datetime.today().replace(tzinfo=None) + timedelta(days=day)
                for interval in range(intervals_per_day):
                    current_time = start_of_day + timedelta(minutes=interval * interval_minutes)
                    # Convert to the desired string format and back to datetime to ensure format
                    formatted_date = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    dates.append(datetime.strptime(formatted_date, '%Y-%m-%d %H:%M:%S'))
        else:
            for day in range(days):
                start_of_day = datetime.today().replace(tzinfo=None) + timedelta(days=day)
                for interval in range(intervals_per_day):
                    current_time = start_of_day + timedelta(minutes=interval * interval_minutes)
                    # Convert to the desired string format and back to datetime to ensure format
                    formatted_date = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    dates.append(datetime.strptime(formatted_date, '%Y-%m-%d %H:%M:%S'))

        return dates