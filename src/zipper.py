import zipfile


class Zipper:
    def zip(self, files_bytes, path):
        with zipfile.ZipFile(path, "w") as zip_file:
            for file_name, file_bytes in files_bytes:
                zip_file.writestr(file_name, file_bytes)
        return path