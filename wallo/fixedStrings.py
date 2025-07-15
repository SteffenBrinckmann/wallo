""" Default configuration for the wallo application. """

defaultConfiguration = {
    'prompts': [
        {
            'name': 'Professional',
            'description': 'Make the text professional',
            'user-prompt': 'Can you make the following paragraph more professional and polished:',
            'attachment':  'selection'
        },
        {
        "name": "summarize_paper",
        "description": "Summarize pdf after uploading it",
        "user-prompt": "Can you summarize the following paper:",
        "attachment":  "pdf"
        }
    ],
    'services': {
        'openAI': {'url':'', 'api':None, 'model': 'gpt-4o'}
    },
  "promptFooter": "\nPlease reply with the html formatted string only",
  "footer": f'\n{"-"*5} Start LLM generated {"-"*5}',
  "header": f'\n{"-"*5}  End LLM generated  {"-"*5}'
}

progressbarInStatusbar = True                    # True to show progress bar in status bar, False for dialog
