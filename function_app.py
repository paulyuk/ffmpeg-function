import os
import logging
import subprocess
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
 

def download_ffmpeg_from_blob(storage_account_name, container_name, blob_name, local_path):
    # Create a credential object
    credential = DefaultAzureCredential()
    
    # Create a BlobServiceClient object
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net/",
        credential=credential
    )
    # Get a blob client
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    
    # Download the blob to a local file
    with open(local_path, "wb") as file_handle:
        download_stream = blob_client.download_blob()
        file_handle.write(download_stream.readall())

def upload_file_to_blob(storage_account_name, container_name, file_path, blob_name):
    credential = DefaultAzureCredential()
    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net/",
        credential=credential
    )
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    return blob_client.url

@app.route(route="ffmpeg_trrigger")
def main(req: func.HttpRequest) -> func.HttpResponse:
    # Azure File Share connection details
    storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    container_name = 'azurefiles'
    blob_name = 'ffmpeg'
    local_ffmpeg_path = '/tmp/ffmpeg'

    # Check if running locally
    if not os.getenv('WEBSITE_INSTANCE_ID'):
        local_ffmpeg_path = os.path.join(os.getcwd(), 'macffmpeg', 'ffmpeg')
        logging.info("Running locally, using FFmpeg from macffmpeg folder")
    else:
        # Download the FFmpeg binary from Azure blob
        try:
            download_ffmpeg_from_blob(storage_account_name, container_name, blob_name, local_ffmpeg_path)
        except Exception as e:
            logging.error(f"Error downloading FFmpeg binary from Azure File Share: {str(e)}")
            return func.HttpResponse(f"Error downloading FFmpeg binary from Azure File Share: {str(e)}", status_code=500)

    # Ensure the file is executable
    try:
        os.chmod(local_ffmpeg_path, 0o755)
    except Exception as e:
        logging.error(f"Error setting executable permissions for FFmpeg binary: {str(e)}")
        return func.HttpResponse(f"Error setting executable permissions for FFmpeg binary: {str(e)}", status_code=500)

   
    # Paths to input photos and output file
    input_photo1 = os.path.join(os.getcwd(), 'photo1.jpg')
    input_photo2 = os.path.join(os.getcwd(), 'photo2.jpg')
    output_photo = '/tmp/output_photo.jpg'
    
    # Check if the output file already exists and delete it
    if os.path.exists(output_photo):
        try:
            os.remove(output_photo)
            logging.info(f"Existing output file {output_photo} deleted.")
        except Exception as e:
            return func.HttpResponse(f"Error deleting existing output file: {str(e)}", status_code=500)

 # Command to resize the images to the same height and merge them side by side using ffmpeg
    command = (
    f"{local_ffmpeg_path} -i {input_photo1} -i {input_photo2} "
    f"-filter_complex '[0:v]scale=-1:1000[scaled1];[1:v]scale=-1:1000[scaled2];[scaled1][scaled2]hstack=inputs=2' "
    f"-frames:v 1 -update 1 {output_photo}"
    )
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"FFmpeg stdout: {result.stdout.decode()}")
        logging.error(f"FFmpeg stderr: {result.stderr.decode()}")
        blob_url = upload_file_to_blob(storage_account_name, container_name, output_photo, 'output_photo.jpg')
        return func.HttpResponse(f"Photos merged successfully: {result.stdout.decode()}", status_code=200)
    except subprocess.CalledProcessError as e:
        error_message = f"ffmpeg execution error: {str(e)}, stdout: {e.stdout.decode()}, stderr: {e.stderr.decode()}"
        logging.error(error_message)
        return func.HttpResponse(error_message, status_code=500)
