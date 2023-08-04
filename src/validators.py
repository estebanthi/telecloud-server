def validate_file_upload(file_data):
    return "type" in file_data and "size" in file_data
