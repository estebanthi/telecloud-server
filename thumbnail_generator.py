import cv2


class ThumbnailGenerator:

    supported_file_types = ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'mpg', 'mpeg', 'm4v', 'webm']

    def check_file_type(self, file_type):
        if file_type in self.supported_file_types:
            return True
        return False

    def generate(self, file_path, file_type):
        if not self.check_file_type(file_type):
            return None

        video = cv2.VideoCapture(file_path)
        success, image = video.read()
        if success:
            cv2.imwrite('temp/thumbnail.jpg', image)
            return 'temp/thumbnail.jpg'
        return None
