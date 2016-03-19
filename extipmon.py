#!/usr/bin/env python
import os
import signal
from ipgetter import myip as get_external_ip
from threading import Thread, RLock
from time import sleep
import geoip
from copy import deepcopy as dcp

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify


APPINDICATOR_ID = 'extipmon'


class ExtIPMon(object):

  def __init__(self):
    self.ext_ip = get_external_ip()
    self.ext_ip_info = geoip.geolite2.lookup(self.ext_ip).get_info_dict()
    print 'Initialized IP info'

    self.thread = Thread(target=self.__loop)
    self.lock = RLock()
    self.is_kill = False

    self.indicator = appindicator.Indicator.new(
      APPINDICATOR_ID,
      os.path.abspath('icon.png'),
      appindicator.IndicatorCategory.SYSTEM_SERVICES
    )
    self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

    # build menu
    self.menu = gtk.Menu()
    # show External IP
    self.menu_item_extip = gtk.MenuItem(self.ext_ip)
    self.menu.append(self.menu_item_extip)
    # show location
    self.menu_item_loc = gtk.MenuItem(self.location_string())
    self.menu.append(self.menu_item_loc)
    # quit
    self.menu_item_quit = gtk.MenuItem('Quit')
    self.menu_item_quit.connect('activate', self.quit)
    self.menu.append(self.menu_item_quit)
    #
    self.menu.show_all()
    self.indicator.set_menu(self.menu)

    notify.init(APPINDICATOR_ID)
    self.thread.start()
    gtk.main()

    with self.lock:
      self.is_kill = True
    sleep(1.0)
    self.thread.join()

  def quit(self, *args):
    notify.uninit()
    gtk.main_quit()

  def location_string(self, info=None):
    if not info:
      info = self.ext_ip_info
    # return ', '.join([info[which]['names']['en'] for which in ['city', 'subdivisions', 'country']])
    return info['city']['names']['en'] + ', ' + \
           info['subdivisions'][0]['names']['en'] + ', ' + \
           info['country']['names']['en']

  def alert(self, old_info):
    new_loc = self.location_string()
    old_loc = self.location_string(info=old_info)
    notify.Notification.new(
      '<b>External IP Address Changed</b>',
      '<i>From:</i> ' + old_loc + '\n<i>To:</i> ' + new_loc,
      None
    ).show()

  def __loop(self):
    while True:
      cur_ext_ip = get_external_ip()
      changed = cur_ext_ip != self.ext_ip
      old_ext_ip = dcp(self.ext_ip)
      self.ext_ip = cur_ext_ip
      with self.lock:
        if self.is_kill:
          return
        if changed:
          old_ext_ip_info = dcp(self.ext_ip_info)
          self.ext_ip_info = geoip.geolite2.lookup(self.ext_ip).get_info_dict()
          print 'IP has changed.'
          print self.ext_ip
          print self.location_string()
          self.menu_item_extip.get_child().set_text(self.ext_ip)
          self.alert(old_info=old_ext_ip_info)
          self.menu_item_loc.get_child().set_text(self.location_string())
      sleep(5.0)




if __name__ == '__main__':
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  app = ExtIPMon()