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
    }
}
