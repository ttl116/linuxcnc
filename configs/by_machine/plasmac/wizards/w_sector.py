#!/usr/bin/env python

'''
w_sector.py

Copyright (C) 2019, 2020  Phillip A Carter

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import os
import gtk
import time
import math
import linuxcnc
import shutil
import hal
from subprocess import Popen,PIPE

class sector_wiz:

    def __init__(self):
        self.i = linuxcnc.ini(os.environ['INI_FILE_NAME'])
        self.c = linuxcnc.command()
        self.s = linuxcnc.stat()
        self.gui = self.i.find('DISPLAY', 'DISPLAY').lower()
        self.configFile = '{}_wizards.cfg'.format(self.i.find('EMC', 'MACHINE').lower())

    def sector_preview(self, event):
        msg = ''
        try:
            if self.liEntry.get_text():
                leadInOffset = math.sin(math.radians(45)) * float(self.liEntry.get_text())
            else:
                leadInOffset = 0.0
        except:
            msg += 'Lead In\n'
        try:
            if self.loEntry.get_text():
                leadOutOffset = math.sin(math.radians(45)) * float(self.loEntry.get_text())
            else:
                leadOutOffset = 0.0
        except:
            msg += 'Lead Out\n'
        try:
            radius = float(self.rEntry.get_text())
        except:
            msg += 'Radius\n'
        try:
            sAngle = math.radians(float(self.sEntry.get_text()))
        except:
            msg += 'Sector Angle\n'
        try:
            if self.aEntry.get_text():
                angle = math.radians(float(self.aEntry.get_text()))
            else:
                angle = 0.0
        except:
            msg  = 'Valid numerical entries required for:\n\n'
            msg += 'Angle\n'
        if msg:
            errMsg = 'Valid numerical entries required for:\n\n{}'.format(msg)
            self.parent.dialog_error('SECTOR', errMsg)
            return
        if radius == 0 or sAngle == 0:
            msg  = 'Valid numerical entries required for:\n\n'
            msg += 'Radius\n'
            msg += 'Sector Angle\n'
            self.parent.dialog_error('SECTOR', msg)
            return
        if self.offset.get_active() and leadInOffset <= 0:
            msg  = 'A Lead In is required if\n\n'
            msg += 'kerf width offset is enabled\n'
            self.parent.dialog_error('SECTOR', msg)
            return
        self.s.poll()
# get current x/y position
        xPos = self.s.actual_position[0] - self.s.g5x_offset[0] - self.s.g92_offset[0]
        yPos = self.s.actual_position[1] - self.s.g5x_offset[1] - self.s.g92_offset[1]
# set origin position
        if self.xSEntry.get_text():
            xO = float(self.xSEntry.get_text())
        else:
            xO = xPos
        if self.ySEntry.get_text():
            yO = float(self.ySEntry.get_text())
        else:
            yO = yPos
# set start point
        xS = xO + (radius * 0.75) * math.cos(angle)
        yS = yO + (radius * 0.75) * math.sin(angle)
# set bottom point
        xB = xO + radius * math.cos(angle)
        yB = yO + radius * math.sin(angle)
# set top point
        xT = xO + radius * math.cos(angle + sAngle)
        yT = yO + radius * math.sin(angle + sAngle)
# set directions
        right = math.radians(0)
        up = math.radians(90)
        left = math.radians(180)
        down = math.radians(270)
        if self.outside.get_active():
            dir = [down, right, left, up]
        else:
            dir = [up, left, right, down]
# set leadin and leadout points
        xIC = xS + (leadInOffset * math.cos(angle + dir[0]))
        yIC = yS + (leadInOffset * math.sin(angle + dir[0]))
        xIS = xIC + (leadInOffset * math.cos(angle + dir[1]))
        yIS = yIC + (leadInOffset * math.sin(angle + dir[1]))
        xOC = xS + (leadOutOffset * math.cos(angle + dir[0]))
        yOC = yS + (leadOutOffset * math.sin(angle + dir[0]))
        xOE = xOC + (leadOutOffset * math.cos(angle + dir[2]))
        yOE = yOC + (leadOutOffset * math.sin(angle + dir[2]))
# setup files and write g-code
        outTmp = open(self.fTmp, 'w')
        outNgc = open(self.fNgc, 'w')
        inWiz = open(self.fNgcBkp, 'r')
        for line in inWiz:
            if '(new wizard)' in line:
                outNgc.write('\n{} (preamble)\n'.format(self.preamble))
                outNgc.write('f#<_hal[plasmac.cut-feed-rate]>\n')
                break
            elif '(postamble)' in line:
                break
            elif 'm2' in line.lower() or 'm30' in line.lower():
                break
            outNgc.write(line)
        outTmp.write('\n(wizard sector)\n')
        outTmp.write('g0 x{:.6f} y{:.6f}\n'.format(xIS, yIS))
        outTmp.write('m3 $0 s1\n')
        if self.offset.get_active():
            outTmp.write('g41.1 d#<_hal[plasmac_run.kerf-width-f]>\n')
        if leadInOffset:
            outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xS, yS, xIC - xIS, yIC - yIS))
        if self.outside.get_active():
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xO, yO))
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xT, yT))
            outTmp.write('g2 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xB, yB, xO - xT, yO - yT))
        else:
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xB, yB))
            outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xT, yT, xO - xB, yO - yB))
            outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xO, yO))
        outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xS, yS))
        if leadOutOffset:
            outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xOE, yOE, xOC - xS, yOC - yS))
        if self.offset.get_active():
            outTmp.write('g40\n')
        outTmp.write('m5\n')
        outTmp.close()
        outTmp = open(self.fTmp, 'r')
        for line in outTmp:
            outNgc.write(line)
        outTmp.close()
        outNgc.write('\n{} (postamble)\n'.format(self.postamble))
        outNgc.write('m2\n')
        outNgc.close()
        self.parent.preview.load(self.fNgc)
        self.add.set_sensitive(True)
        self.parent.xOrigin = self.xSEntry.get_text()
        self.parent.yOrigin = self.ySEntry.get_text()

    def auto_preview(self, widget):
        if self.rEntry.get_text() and self.sEntry.get_text():
            self.sector_preview('auto') 

    def entry_changed(self, widget):
        if not self.liEntry.get_text() or float(self.liEntry.get_text()) == 0:
            self.offset.set_sensitive(False)
        else:
            self.offset.set_sensitive(True)
        self.parent.entry_changed(widget)

    def sector_show(self, parent, entries, fNgc, fNgcBkp, fTmp, rowS, xOrigin, yOrigin):
        entries.set_row_spacings(rowS)
        self.parent = parent
        for child in entries.get_children():
            entries.remove(child)
        self.fNgc = fNgc
        self.fNgcBkp = fNgcBkp
        self.fTmp = fTmp
        self.sRadius = 0.0
        self.hSpeed = 100
        cutLabel = gtk.Label('Cut Type')
        cutLabel.set_alignment(0.95, 0.5)
        cutLabel.set_width_chars(8)
        entries.attach(cutLabel, 0, 1, 0, 1)
        self.outside = gtk.RadioButton(None, 'Outside')
        self.outside.connect('toggled', self.auto_preview)
        entries.attach(self.outside, 1, 2, 0, 1)
        inside = gtk.RadioButton(self.outside, 'Inside')
        entries.attach(inside, 2, 3, 0, 1)
        offsetLabel = gtk.Label('Offset')
        offsetLabel.set_alignment(0.95, 0.5)
        offsetLabel.set_width_chars(8)
        entries.attach(offsetLabel, 3, 4, 0, 1)
        self.offset = gtk.CheckButton('Kerf')
        self.offset.connect('toggled', self.auto_preview)
        entries.attach(self.offset, 4, 5, 0, 1)
        lLabel = gtk.Label('Lead In')
        lLabel.set_alignment(0.95, 0.5)
        lLabel.set_width_chars(8)
        entries.attach(lLabel, 0, 1, 1, 2)
        self.liEntry = gtk.Entry()
        self.liEntry.set_width_chars(8)
        self.liEntry.connect('activate', self.auto_preview)
        self.liEntry.connect('changed', self.entry_changed)
        entries.attach(self.liEntry, 1, 2, 1, 2)
        loLabel = gtk.Label('Lead Out')
        loLabel.set_alignment(0.95, 0.5)
        loLabel.set_width_chars(8)
        entries.attach(loLabel, 0, 1, 2, 3)
        self.loEntry = gtk.Entry()
        self.loEntry.set_width_chars(8)
        self.loEntry.connect('activate', self.auto_preview)
        self.loEntry.connect('changed', self.parent.entry_changed)
        entries.attach(self.loEntry, 1, 2, 2, 3)
        xSLabel = gtk.Label()
        xSLabel.set_markup('X <span foreground="red">origin</span>')
        xSLabel.set_alignment(0.95, 0.5)
        xSLabel.set_width_chars(8)
        entries.attach(xSLabel, 0, 1, 3, 4)
        self.xSEntry = gtk.Entry()
        self.xSEntry.set_width_chars(8)
        self.xSEntry.connect('activate', self.auto_preview)
        self.xSEntry.connect('changed', self.parent.entry_changed)
        entries.attach(self.xSEntry, 1, 2, 3, 4)
        ySLabel = gtk.Label()
        ySLabel.set_markup('Y <span foreground="red">origin</span>')
        ySLabel.set_alignment(0.95, 0.5)
        ySLabel.set_width_chars(8)
        entries.attach(ySLabel, 0, 1, 4, 5)
        self.ySEntry = gtk.Entry()
        self.ySEntry.set_width_chars(8)
        self.ySEntry.connect('activate', self.auto_preview)
        self.ySEntry.connect('changed', self.parent.entry_changed)
        entries.attach(self.ySEntry, 1, 2, 4, 5)
        rLabel = gtk.Label('Radius')
        rLabel.set_alignment(0.95, 0.5)
        rLabel.set_width_chars(8)
        entries.attach(rLabel, 0, 1, 5, 6)
        self.rEntry = gtk.Entry()
        self.rEntry.set_width_chars(8)
        self.rEntry.connect('activate', self.auto_preview)
        self.rEntry.connect('changed', self.parent.entry_changed)
        entries.attach(self.rEntry, 1, 2, 5, 6)
        sLabel = gtk.Label('Sector Angle')
        sLabel.set_alignment(0.95, 0.5)
        sLabel.set_width_chars(8)
        entries.attach(sLabel, 0, 1, 6, 7)
        self.sEntry = gtk.Entry()
        self.sEntry.set_width_chars(8)
        self.sEntry.connect('activate', self.auto_preview)
        self.sEntry.connect('changed', self.parent.entry_changed)
        entries.attach(self.sEntry, 1, 2, 6, 7)
        aLabel = gtk.Label('Angle')
        aLabel.set_alignment(0.95, 0.5)
        aLabel.set_width_chars(8)
        entries.attach(aLabel, 0, 1, 7, 8)
        self.aEntry = gtk.Entry()
        self.aEntry.set_width_chars(8)
        self.aEntry.set_text('0')
        self.aEntry.connect('activate', self.auto_preview)
        self.aEntry.connect('changed', self.parent.entry_changed)
        entries.attach(self.aEntry, 1, 2, 7, 8)
        preview = gtk.Button('Preview')
        preview.connect('pressed', self.sector_preview)
        entries.attach(preview, 0, 1, 13, 14)
        self.add = gtk.Button('Add')
        self.add.set_sensitive(False)
        self.add.connect('pressed', self.parent.add_shape_to_file, self.add)
        entries.attach(self.add, 2, 3, 13, 14)
        undo = gtk.Button('Undo')
        undo.connect('pressed', self.parent.undo_shape, self.add)
        entries.attach(undo, 4, 5, 13, 14)
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(
                filename='./wizards/images/sector.png', 
                width=240, 
                height=240)
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        entries.attach(image, 2, 5, 1, 9)
        if os.path.exists(self.configFile):
            f_in = open(self.configFile, 'r')
            for line in f_in:
                if line.startswith('preamble'):
                    self.preamble = line.strip().split('=')[1]
                elif line.startswith('postamble'):
                    self.postamble = line.strip().split('=')[1]
                elif line.startswith('lead-in'):
                    self.liEntry.set_text(line.strip().split('=')[1])
                elif line.startswith('lead-out'):
                    self.loEntry.set_text(line.strip().split('=')[1])
        self.xSEntry.set_text('{:0.3f}'.format(float(xOrigin)))
        self.ySEntry.set_text('{:0.3f}'.format(float(yOrigin)))
        if not self.liEntry.get_text() or float(self.liEntry.get_text()) == 0:
            self.offset.set_sensitive(False)
        self.parent.undo_shape(None, self.add)
        self.parent.W.show_all()
        self.rEntry.grab_focus()
