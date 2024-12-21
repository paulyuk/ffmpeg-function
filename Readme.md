# Sample to download and use FFMPEG in Azure Function

## Prerequistes
1) Azure Developer CLI
2) Python 3.9+
3) Azure Functions Core Tools

## Running the sample
1) Set permissions for scripts to execute

```shell
chmod +x ./infra/scripts/*.sh
```

2) Provision all resources needed

```shell
azd provision
```

Ensure your local.settings.json match the .env file created in the .azure folder after provisioning.

3) If running the first time, ensure Linux `ffmpeg` executable is copied to your storage account and blob container.  (TODO: make a function to initialize the container with the executable)

4) Start the function

Press F5 or run from command line

```shell
func start
```

Run the function.  You should see message `Photos merged successfully: `