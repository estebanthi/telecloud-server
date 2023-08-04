import io


class Chunker:
    def __init__(self, chunk_size):
        self.chunk_size = chunk_size

    def split(self, file):
        chunks = []
        while True:
            chunk = file.read(self.chunk_size)
            if not chunk:
                break
            chunks.append(chunk)
        return chunks

    @staticmethod
    def join(chunks):
        file = io.BytesIO()
        for chunk in chunks:
            with open(chunk, "rb") as f:
                file.write(f.read())
        file.seek(0)
        return file.read()
