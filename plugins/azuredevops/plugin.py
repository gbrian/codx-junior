from plugins.azuredevops.azure_devops_pull_requests_plugin import AzureDevopsPullRequestPlugin


def get_pull_request_comments(**kwrags):
   azp = AzureDevopsPullRequestPlugin(**kwrags)
   return apz.apply_pr_comments_to_files(pr_url=kwargs["pr_url"])