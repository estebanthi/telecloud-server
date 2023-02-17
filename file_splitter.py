import io


class FileSplitter:
    def __init__(self, max_size):
        self.max_size = max_size

    def split(self, file):
        chunks = []
        while True:
            chunk = file.read(self.max_size)
            if not chunk:
                break
            chunks.append(chunk)
        return chunks

    @staticmethod
    def join(chunks):
        file = io.BytesIO()
        for chunk in chunks:
            file.write(chunk)
        file.seek(0)
        return file
