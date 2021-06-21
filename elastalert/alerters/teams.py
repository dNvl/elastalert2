import json
import requests
import os

from elastalert.alerts import Alerter, DateTimeEncoder
from elastalert.util import EAException, elastalert_logger
from requests.exceptions import RequestException


class MsTeamsAlerter(Alerter):
    """ Creates a Microsoft Teams Conversation Message for each alert """
    required_options = frozenset(['ms_teams_webhook_url'])

    def __init__(self, rule):
        super(MsTeamsAlerter, self).__init__(rule)

        teams_settings = {'ms_teams_webhook_url': None,
                          'ms_teams_proxy': None}

        teams_settings['ms_teams_webhook_url'] = self.rule.get('ms_teams_webhook_url', None)
        teams_settings['ms_teams_proxy'] = self.rule.get('ms_teams_proxy', None)

        # Optional overwrite the settings using environment variable values
        self.ms_teams_env_prefix = self.rule.get('ms_teams_env_prefix', None)
        if self.ms_teams_env_prefix is not None:
            webhookUrl = os.environ.get(self.ms_teams_env_prefix + '_MS_TEAMS_WEBHOOK_URL')
            if webhookUrl is not None:
                teams_settings['ms_teams_webhook_url'] = webhookUrl

            webhookProxy = os.environ.get(self.ms_teams_env_prefix + '_MS_TEAMS_PROXY')
            if webhookProxy is not None:
                teams_settings['ms_teams_proxy'] = webhookProxy

        self.ms_teams_webhook_url = None
        if isinstance(teams_settings['ms_teams_webhook_url'], str):
            self.ms_teams_webhook_url = [teams_settings['ms_teams_webhook_url']]

        self.ms_teams_proxy = teams_settings['ms_teams_proxy']

        self.ms_teams_alert_summary = self.rule.get('ms_teams_alert_summary', 'ElastAlert Message')
        self.ms_teams_alert_fixed_width = self.rule.get('ms_teams_alert_fixed_width', False)
        self.ms_teams_theme_color = self.rule.get('ms_teams_theme_color', '')

    def format_body(self, body):
        if self.ms_teams_alert_fixed_width:
            body = body.replace('`', "'")
            body = "```{0}```".format('```\n\n```'.join(x for x in body.split('\n'))).replace('\n``````', '')
        return body

    def alert(self, matches):
        body = self.create_alert_body(matches)

        body = self.format_body(body)
        # post to Teams
        headers = {'content-type': 'application/json'}
        # set https proxy, if it was provided
        proxies = {'https': self.ms_teams_proxy} if self.ms_teams_proxy else None
        payload = {
            '@type': 'MessageCard',
            '@context': 'http://schema.org/extensions',
            'summary': self.ms_teams_alert_summary,
            'title': self.create_title(matches),
            'text': body
        }
        if self.ms_teams_theme_color != '':
            payload['themeColor'] = self.ms_teams_theme_color

        for url in self.ms_teams_webhook_url:
            try:
                response = requests.post(url, data=json.dumps(payload, cls=DateTimeEncoder), headers=headers, proxies=proxies)
                response.raise_for_status()
            except RequestException as e:
                raise EAException("Error posting to ms teams: %s" % e)
        elastalert_logger.info("Alert sent to MS Teams")

    def get_info(self):
        return {'type': 'ms_teams',
                'ms_teams_webhook_url': self.ms_teams_webhook_url}
