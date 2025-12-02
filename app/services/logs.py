import os

from app.config import log_file_path

log_line_count = 0
last_processed_log_line_count = 0



class LogEntry:
    def __init__(self):
        self.arena_ids = None
        self.actions_dict = None
        self.current_line = None
        self.current_line_number = 0
        self.log_line_count = 0
        self.last_processed_log_line_count = 0
        self.file_handle = None
        
        if self.file_handle is None and log_file_path.exists():
            self.file_handle = open(log_file_path, 'rb')
            self.log_line_count = sum(1 for _ in self.file_handle)
            self.file_handle.seek(0, os.SEEK_END)
            self.current_line_number = self.log_line_count
      
        if self.file_handle and self.current_line is None:
            self.file_handle.seek(-2, os.SEEK_END)
            while self.file_handle.read(1) != b'\n':
                if self.file_handle.tell() == 1:
                    self.file_handle.seek(0)
                    break
                self.file_handle.seek(-2, os.SEEK_CUR)

            self.current_line = self.file_handle.readline().decode('utf-8').strip()
            self.set_last_processed_count(self.current_line_number)
            # self.current_line_number -= 1
            
        
    def read_next_last_line(self):
        if self.file_handle and self.current_line_number > 0:
            self.file_handle.seek(-2, os.SEEK_END)
            while self.file_handle.read(1) != b'\n':
                if self.file_handle.tell() == 1:
                    self.file_handle.seek(0)
                    break
                self.file_handle.seek(-2, os.SEEK_CUR)

            self.current_line = self.file_handle.readline().decode('utf-8').strip()
            self.set_last_processed_count(self.current_line_number)
            # self.current_line_number -= 1
            

    def parse_cards_log_line(self, log_line):
        try:
            log_segments = log_line.split("::")
            if len(log_segments) < 3:
                return []

            cards_section = log_segments[2].split(": ")
            if len(cards_section) < 2:
                return []
            
            if "cards" in log_line:
                arena_ids_str = cards_section[1].strip("[]")
                self.arena_ids = [id.strip() for id in arena_ids_str.split(", ") if id.strip()]
                return self.arena_ids

        except (IndexError, AttributeError):
            return []

    def parse_actions_log_line(self, log_line):
        import jsonpickle
        try:
            log_segments = log_line.split("::")
            if len(log_segments) < 3:
                return []
            actions_section = log_segments[2]
            if "actions" in log_line:
                actions_str = actions_section.split("actions: ")[1]
                self.actions_dict = jsonpickle.decode(actions_str)
                return self.actions_dict
        except (IndexError, AttributeError):
            return []


    def get_log_line_count(self) -> int:
        return self.log_line_count

    def get_last_processed_count(self) -> int:
        return self.last_processed_log_line_count

    # def set_last_processed_count(count: int) -> None:
    #     global last_processed_log_line_count
    #     last_processed_log_line_count = count

    def set_last_processed_count(self, count: int) -> None:
        self.last_processed_log_line_count = count




async def get_last_log_line() -> str | None:
    global log_line_count
    try:
        if not log_file_path.exists():
            return None

        with open(log_file_path, 'rb') as file:
            log_line_count = sum(1 for _ in file)

            file.seek(0, os.SEEK_END)
            file_size = file.tell()

            if file_size == 0:
                return None

            file.seek(-2, os.SEEK_END)
            while file.read(1) != b'\n':
                if file.tell() == 1:
                    file.seek(0)
                    break
                file.seek(-2, os.SEEK_CUR)

            last_line = file.readline().decode('utf-8').strip()
            return last_line
    except Exception as e:
        print(f"Error reading log file: {e}")
        return None


def parse_arena_ids_from_log(log_entry: str) -> list[str]:
    try:
        log_segments = log_entry.split("::")
        if len(log_segments) < 3:
            return []

        cards_section = log_segments[2].split(": ")
        if len(cards_section) < 2:
            return []

        arena_ids_str = cards_section[1].strip("[]")
        return [id.strip() for id in arena_ids_str.split(", ") if id.strip()]
    except (IndexError, AttributeError):
        return []


async def get_log_line_count() -> int:
    return log_line_count


def get_last_processed_count() -> int:
    return last_processed_log_line_count


async def set_last_processed_count(count: int) -> None:
    global last_processed_log_line_count
    last_processed_log_line_count = count