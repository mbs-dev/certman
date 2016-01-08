#!coding: utf-8

from terminaltables import AsciiTable

from certman.manager import Manager
from certman.settings import SETTINGS

class Certman(object):
    """
    This class represents CLI for Certman. It loops over input waiting for
    commands and execute them delegating to manager instance
    """

    COMMANDS = (
        ('addcert', 'add new certificate today'),
        ('report', 'generate this week report'),
        ('delete', 'delete certificate by ID or email'),
        ('settings', 'show current settings'),
        ('help', 'show this help'),
        ('exit', 'exit')
    )

    def __init__(self):
        self.manager = Manager()

    def print_banner(self):
        print "Certificates Manager v.0.1"
        print "Builds.io Team. This is proprietary software."
        print
        print "Send bugs to: <ya.na.pochte@gmail.com> Vladimir Ignatev"
        print "==="

    def print_help(self):
        for command in self.COMMANDS:
            print "%s - %s" % command

    def input(self):
        user_input = ''
        while not user_input:
            user_input = raw_input('> ').strip().lower()

        return user_input

    def run(self):
        self.print_banner()
        self.print_help()

        while True:
            command = self.input()

            if command == 'addcert':
                count = self.manager.command_addcert()
                print "Successfully added %s certificates" % count

            elif command == 'settings':
                print SETTINGS

            elif command == 'help':
                self.print_banner()
                self.print_help()

            elif command == 'report':
                rows, week_start, week_end, total = self.manager.command_report()
                table = AsciiTable(rows, 'Certificates obtained %s-%s' % (week_start, week_end))
                table.outer_border = False
                print table.table
                print "\nTotal certificates obtained: %s" % total

            elif command == 'delete':
                self.manager.command_delete()

            elif command == 'exit':
                return 0
            else:
                pass
