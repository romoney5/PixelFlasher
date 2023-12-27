#!/usr/bin/env python

import wx
import wx.stc as stc
import traceback
import images as images
import json
import json5
import re
from datetime import datetime
from runtime import *

# ============================================================================
#                               Class PifManager
# ============================================================================
class PifManager(wx.Dialog):
    def __init__(self, *args, parent=None, config=None, **kwargs):
        self.config = config
        wx.Dialog.__init__(self, parent, *args, **kwargs, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.config = config
        self.SetTitle("Pif Manager")
        self.pif_json_path = PIF_JSON_PATH
        self.device_pif = ''
        self.pi_app = 'gr.nikolasspyr.integritycheck'
        self.coords = Coords()
        self.enable_buttons = False
        self.pif_exists = False
        self.advanced_props_support = False
        self.favorite_pifs = get_favorite_pifs()
        self.insync = False

        # Active pif label
        self.active_pif_label = wx.StaticText(parent=self, id=wx.ID_ANY, label=u"Active Pif")
        self.active_pif_label.SetToolTip(u"Loaded Pif (from Device)")
        font = wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.active_pif_label.SetFont(font)
        # Modified status
        self.pif_modified_image = wx.StaticBitmap(parent=self)
        self.pif_modified_image.SetBitmap(images.alert_gray_24.GetBitmap())
        self.pif_modified_image.SetToolTip(u"Active pif is not modified.")
        # Module version label
        self.pif_version_label = wx.StaticText(parent=self, id=wx.ID_ANY, label=u"", style=wx.ST_ELLIPSIZE_END)
        self.pif_version_label.SetToolTip(u"Pif Module")
        # Favorite button
        self.favorite_pif_button = wx.BitmapButton(parent=self, id=wx.ID_ANY, bitmap=wx.NullBitmap, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.BU_AUTODRAW)
        self.favorite_pif_button.SetBitmap(images.heart_gray_24.GetBitmap())
        self.favorite_pif_button.SetToolTip(u"Active pif is not saved in favorites.")
        # Combo Box of favorites
        pif_labels = [pif["label"] for pif in self.favorite_pifs.values()]
        self.pif_combo_box = wx.ComboBox(self, choices=pif_labels, style=wx.CB_READONLY)
        # Import button
        self.import_pif_button = wx.BitmapButton(parent=self, id=wx.ID_ANY, bitmap=wx.NullBitmap, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.BU_AUTODRAW)
        self.import_pif_button.SetBitmap(images.import_24.GetBitmap())
        self.import_pif_button.SetToolTip(u"Select a folder to import pif json files.")

        # Active Pif
        self.active_pif_stc = stc.StyledTextCtrl(self)
        self.active_pif_stc.SetLexer(stc.STC_LEX_JSON)
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_DEFAULT, "fore:#000000")
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_NUMBER, "fore:#007F7F")
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_STRING, "fore:#7F007F")
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_PROPERTYNAME, "fore:#007F00")
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_ESCAPESEQUENCE, "fore:#7F7F00")
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_KEYWORD, "fore:#00007F,bold")
        self.active_pif_stc.StyleSetSpec(stc.STC_JSON_OPERATOR, "fore:#7F0000")
        self.active_pif_stc.SetCaretForeground(wx.BLACK)
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.active_pif_stc.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, font)
        self.active_pif_stc.SetWrapMode(wx.stc.STC_WRAP_NONE)
        self.active_pif_stc.SetUseHorizontalScrollBar(True)
        self.active_pif_stc.SetTabWidth(4)
        self.active_pif_stc.SetIndent(4)

        # Console label
        self.console_label = wx.StaticText(parent=self, id=wx.ID_ANY, label=u"Output")
        self.console_label.SetToolTip(u"Console Output:\nIt could be the json output of processed prop\or it could be the Play Integrity Check result.\n\nThis is not what currently is on the device.")
        font = wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.console_label.SetFont(font)
        # Paste Up
        self.paste_up = wx.BitmapButton(parent=self, id=wx.ID_ANY, bitmap=wx.NullBitmap, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.BU_AUTODRAW)
        self.paste_up.SetBitmap(images.paste_up_24.GetBitmap())
        self.paste_up.SetToolTip(u"Paste the console window content to Active pif.")
        self.paste_up.Enable(False)
        # Paste Down
        self.paste_down = wx.BitmapButton(parent=self, id=wx.ID_ANY, bitmap=wx.NullBitmap, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.BU_AUTODRAW)
        self.paste_down.SetBitmap(images.paste_down_24.GetBitmap())
        self.paste_down.SetToolTip(u"Paste the Active pif to console window.")
        self.paste_down.Enable(False)
        # Reprocess
        self.reprocess = wx.BitmapButton(parent=self, id=wx.ID_ANY, bitmap=wx.NullBitmap, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.BU_AUTODRAW)
        self.reprocess.SetBitmap(images.scan_24.GetBitmap())
        self.reprocess.SetToolTip(u"Reprocess current console window json.\nUseful if you changed module version which might required additional / different fields.")
        self.reprocess.Enable(False)
        # Add missing keys checkbox
        self.add_missing_keys_checkbox = wx.CheckBox(parent=self, id=wx.ID_ANY, label=u"Add missing Keys from device", pos=wx.DefaultPosition, size=wx.DefaultSize, style=0)
        self.add_missing_keys_checkbox.SetToolTip(u"When Processing or Reprocessing, add missing fields from device.")

        # Console
        self.console_stc = stc.StyledTextCtrl(self)
        self.console_stc.SetLexer(stc.STC_LEX_JSON)
        self.console_stc.StyleSetSpec(stc.STC_JSON_DEFAULT, "fore:#000000")
        self.console_stc.StyleSetSpec(stc.STC_JSON_NUMBER, "fore:#007F7F")
        self.console_stc.StyleSetSpec(stc.STC_JSON_STRING, "fore:#7F007F")
        self.console_stc.StyleSetSpec(stc.STC_JSON_PROPERTYNAME, "fore:#007F00")
        self.console_stc.StyleSetSpec(stc.STC_JSON_ESCAPESEQUENCE, "fore:#7F7F00")
        self.console_stc.StyleSetSpec(stc.STC_JSON_KEYWORD, "fore:#00007F,bold")
        self.console_stc.StyleSetSpec(stc.STC_JSON_OPERATOR, "fore:#7F0000")
        self.console_stc.SetCaretForeground(wx.BLACK)
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.console_stc.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, font)
        self.console_stc.SetWrapMode(wx.stc.STC_WRAP_NONE)
        self.console_stc.SetUseHorizontalScrollBar(True)
        self.console_stc.SetTabWidth(4)
        self.console_stc.SetIndent(4)

        # Ok button
        self.close_button = wx.Button(self, wx.ID_ANY, u"Close", wx.DefaultPosition, wx.DefaultSize, 0)

        # Create pif.json button
        self.create_pif_button = wx.Button(self, wx.ID_ANY, u"Create pif.json", wx.DefaultPosition, wx.DefaultSize, 0)
        self.create_pif_button.SetToolTip(u"Create pif.json")
        self.create_pif_button.Enable(False)

        # Reload pif.json button
        self.reload_pif_button = wx.Button(self, wx.ID_ANY, u"Reload pif.json", wx.DefaultPosition, wx.DefaultSize, 0)
        self.reload_pif_button.SetToolTip(u"Reload pif.json from device.")
        self.reload_pif_button.Enable(False)

        # Process build.prop button
        self.process_build_prop_button = wx.Button(self, wx.ID_ANY, u"Process build.prop(s)", wx.DefaultPosition, wx.DefaultSize, 0)
        self.process_build_prop_button.SetToolTip(u"Process build.prop to extract pif.json.")

        # Check for Auto Push pif.json
        self.auto_push_pif_checkbox = wx.CheckBox(parent=self, id=wx.ID_ANY, label=u"Auto Update pif.json", pos=wx.DefaultPosition, size=wx.DefaultSize, style=0)
        self.auto_push_pif_checkbox.SetToolTip(u"After Processing build.props, the pif.json is automatically pushed to the device and the GMS process is killed.")
        self.auto_push_pif_checkbox.Enable(False)

        # Check for Auto Check Play Integrity
        self.auto_check_pi_checkbox = wx.CheckBox(parent=self, id=wx.ID_ANY, label=u"Auto Check Play Integrity", pos=wx.DefaultPosition, size=wx.DefaultSize, style=0)
        self.auto_check_pi_checkbox.SetToolTip(u"After saving (pushing) pif.json, automatically run Play Integrity Check.")
        self.auto_check_pi_checkbox.Enable(False)

        # option button PI Selectedion
        self.pi_option = wx.RadioBox(self, choices=["Play Integrity API Checker", "Simple Play Integrity Checker", "TB Checker", "Play Store", "YASNAC"], style=wx.RA_VERTICAL)

        # Skip getting results checkbox
        self.disable_uiautomator_checkbox = wx.CheckBox(parent=self, id=wx.ID_ANY, label=u"Disable UIAutomator", pos=wx.DefaultPosition, size=wx.DefaultSize, style=0)
        self.disable_uiautomator_checkbox.SetToolTip(u"Disables UIAutomator\nThis is useful for devices with buggy UIAutomator.\nNOTE: Create the coords.json file manually to make use of automated testing.")

        # Play Integrity API Checker button
        self.pi_checker_button = wx.Button(self, wx.ID_ANY, u"Play Integrity Check", wx.DefaultPosition, wx.DefaultSize, 0)
        self.pi_checker_button.SetToolTip(u"Play Integrity API Checker\nNote: Need to install app from Play store.")

        # Get Xiaomi Pif button
        self.xiaomi_pif_button = wx.Button(self, wx.ID_ANY, u"Get Xiaomi Pif", wx.DefaultPosition, wx.DefaultSize, 0)
        self.xiaomi_pif_button.SetToolTip(u"Get Xiaomi.eu pif\nEasy to start but is not recommended as it gets banned quickly.\nRecommended to find your own.")

        # Get TheFreeman193 Pif button
        self.freeman_pif_button = wx.Button(self, wx.ID_ANY, u"Get TheFreeman193 Random Pif", wx.DefaultPosition, wx.DefaultSize, 0)
        self.freeman_pif_button.SetToolTip(u"Get a random pif from TheFreeman193 repository.\nNote: The pif might or might not work.")

        # Make the buttons the same size
        button_width = self.pi_option.GetSize()[0] + 10
        self.create_pif_button.SetMinSize((button_width, -1))
        self.reload_pif_button.SetMinSize((button_width, -1))
        self.process_build_prop_button.SetMinSize((button_width, -1))
        self.auto_push_pif_checkbox.SetMinSize((button_width, -1))
        self.auto_check_pi_checkbox.SetMinSize((button_width, -1))
        self.disable_uiautomator_checkbox.SetMinSize((button_width, -1))
        self.pi_checker_button.SetMinSize((button_width, -1))
        self.xiaomi_pif_button.SetMinSize((button_width, -1))
        self.freeman_pif_button.SetMinSize((button_width, -1))

        h_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_buttons_sizer.Add((0, 0), 1, wx.EXPAND, 10)
        h_buttons_sizer.Add(self.close_button, 0, wx.ALL, 20)
        h_buttons_sizer.Add((0, 0), 1, wx.EXPAND, 10)

        v_buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        v_buttons_sizer.Add(self.create_pif_button, 0, wx.TOP | wx.RIGHT, 10)
        v_buttons_sizer.Add(self.reload_pif_button, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 10)
        v_buttons_sizer.AddStretchSpacer()
        v_buttons_sizer.Add(self.process_build_prop_button, 0, wx.TOP | wx.RIGHT, 10)
        v_buttons_sizer.Add(self.auto_push_pif_checkbox, 0, wx.ALL, 10)
        v_buttons_sizer.Add(self.auto_check_pi_checkbox, 0, wx.ALL, 10)
        v_buttons_sizer.Add(self.pi_option, 0, wx.TOP, 10)
        v_buttons_sizer.Add(self.disable_uiautomator_checkbox, 0, wx.TOP | wx.BOTTOM | wx.RIGHT, 10)
        v_buttons_sizer.Add(self.pi_checker_button, 0, wx.TOP | wx.BOTTOM | wx.RIGHT, 10)
        v_buttons_sizer.Add(self.xiaomi_pif_button, 0, wx.TOP | wx.BOTTOM | wx.RIGHT, 10)
        v_buttons_sizer.Add(self.freeman_pif_button, 0, wx.TOP | wx.BOTTOM | wx.RIGHT, 10)

        console_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        console_label_sizer.AddSpacer(10)
        console_label_sizer.Add(self.console_label, 0, wx.ALIGN_CENTER_VERTICAL)
        console_label_sizer.AddSpacer(10)
        console_label_sizer.Add(self.paste_up, 0, wx.ALIGN_CENTER_VERTICAL)
        console_label_sizer.AddSpacer(10)
        console_label_sizer.Add(self.paste_down, 0, wx.ALIGN_CENTER_VERTICAL)
        console_label_sizer.AddSpacer(10)
        console_label_sizer.Add(self.reprocess, 0, wx.ALIGN_CENTER_VERTICAL)
        console_label_sizer.AddSpacer(10)
        console_label_sizer.Add(self.add_missing_keys_checkbox, 0, wx.ALIGN_CENTER_VERTICAL)

        stc_sizer = wx.BoxSizer(wx.VERTICAL)
        stc_sizer.Add(self.active_pif_stc, 1, wx.EXPAND | wx.ALL, 10)
        stc_sizer.Add(console_label_sizer, 0, wx.TOP, 10)
        stc_sizer.Add(self.console_stc, 1, wx.EXPAND | wx.ALL, 10)

        outside_stc_sizer = wx.BoxSizer(wx.HORIZONTAL)
        outside_stc_sizer.Add(stc_sizer, 1, wx.EXPAND | wx.ALL, 0)
        outside_stc_sizer.Add(v_buttons_sizer, 0, wx.EXPAND | wx.ALL, 0)

        active_pif_label_sizer = wx.BoxSizer(wx.HORIZONTAL)
        active_pif_label_sizer.AddSpacer(10)
        active_pif_label_sizer.Add(self.active_pif_label, 0, wx.ALIGN_CENTER_VERTICAL)
        active_pif_label_sizer.AddSpacer(10)
        active_pif_label_sizer.Add(self.pif_modified_image, 0, wx.ALIGN_CENTER_VERTICAL)
        active_pif_label_sizer.AddSpacer(100)
        active_pif_label_sizer.Add(self.pif_version_label, 1, wx.EXPAND)
        active_pif_label_sizer.AddSpacer(100)
        active_pif_label_sizer.Add(self.favorite_pif_button, 0, wx.ALIGN_CENTER_VERTICAL)
        active_pif_label_sizer.AddSpacer(10)
        active_pif_label_sizer.Add(self.pif_combo_box, 1, wx.EXPAND)
        active_pif_label_sizer.AddSpacer(10)
        active_pif_label_sizer.Add(self.import_pif_button, 0, wx.ALIGN_CENTER_VERTICAL)

        vSizer = wx.BoxSizer(wx.VERTICAL)
        vSizer.Add(active_pif_label_sizer, 0, wx.TOP, 10)
        vSizer.Add(outside_stc_sizer, 1, wx.EXPAND, 0)
        vSizer.Add(h_buttons_sizer, 0, wx.EXPAND, 10)

        self.SetSizer(vSizer)
        self.SetMinSize((400, 300))
        self.Layout()
        self.Centre(wx.BOTH)

        # Connect Events
        self.close_button.Bind(wx.EVT_BUTTON, self.onClose)
        self.create_pif_button.Bind(wx.EVT_BUTTON, self.CreatePifJson)
        self.reload_pif_button.Bind(wx.EVT_BUTTON, self.LoadReload)
        self.process_build_prop_button.Bind(wx.EVT_BUTTON, self.ProcessBuildProp)
        self.pi_checker_button.Bind(wx.EVT_BUTTON, self.PlayIntegrityCheck)
        self.xiaomi_pif_button.Bind(wx.EVT_BUTTON, self.XiaomiPif)
        self.freeman_pif_button.Bind(wx.EVT_BUTTON, self.FreemanPif)
        self.pi_option.Bind(wx.EVT_RADIOBOX, self.TestSelection)
        self.Bind(wx.EVT_SIZE, self.onResize)
        self.Bind(wx.EVT_SHOW, self.onShow)
        self.paste_up.Bind(wx.EVT_BUTTON, self.PasteUp)
        self.paste_down.Bind(wx.EVT_BUTTON, self.PasteDown)
        self.reprocess.Bind(wx.EVT_BUTTON, self.ReProcess)
        self.favorite_pif_button.Bind(wx.EVT_BUTTON, self.Favorite)
        self.active_pif_stc.Bind(wx.stc.EVT_STC_CHANGE, self.ActivePifStcChange)
        self.console_stc.Bind(wx.stc.EVT_STC_CHANGE, self.ConsoleStcChange)
        self.pif_combo_box.Bind(wx.EVT_COMBOBOX, self.PifComboBox)
        self.import_pif_button.Bind(wx.EVT_BUTTON, self.ImportFavorites)

        # init button states
        self.init()

        # Autosize the dialog
        self.active_pif_stc.PostSizeEventToParent()
        self.SetSizerAndFit(vSizer)

        print("\nOpening Pif Manager ...")

    # -----------------------------------------------
    #              Function onShow
    # -----------------------------------------------
    def onShow(self, event):
        if self.IsShown():
            if self.config:
                size = (self.config.pif_width, self.config.pif_height)
            else:
                size=(PIF_WIDTH, PIF_HEIGHT)
            self.SetSize(size)
        event.Skip()

    # -----------------------------------------------
    #              Function init
    # -----------------------------------------------
    def init(self, refresh=False):
        device = get_phone()
        if not device.rooted:
            return
        modules = device.get_magisk_detailed_modules(refresh)

        self.create_pif_button.Enable(True)
        self.reload_pif_button.Enable(False)
        self.auto_push_pif_checkbox.Enable(False)
        self.auto_check_pi_checkbox.Enable(False)
        self.pi_checker_button.Enable(False)
        self.enable_buttons = False
        self.pif_version_label.SetLabel('')

        if modules:
            for module in modules:
                if module.id == "playintegrityfix" and "Play Integrity" in module.name:
                    if module.name == "Play Integrity Fork":
                        self.pif_json_path = '/data/adb/modules/playintegrityfix/custom.pif.json'
                        if int(module.versionCode) > 4000:
                            print("Advanced props support enabled.")
                            self.advanced_props_support = True
                    elif module.name != "Play Integrity NEXT":
                        self.pif_json_path = '/data/adb/pif.json'
                    if module.version in ["PROPS-v2.1", "PROPS-v2.0"]:
                        self.pif_json_path = '/data/adb/modules/playintegrityfix/pif.json'
                    self.create_pif_button.Enable(False)
                    self.reload_pif_button.Enable(True)
                    self.auto_push_pif_checkbox.Enable(True)
                    self.auto_check_pi_checkbox.Enable(True)
                    self.pi_checker_button.Enable(True)
                    self.enable_buttons = True
                    self.pif_version_label.SetLabel(f"{module.name} {module.version} {module.versionCode}")
                    self.check_pif_json()
                    if self.pif_exists:
                        self.LoadReload(None)
                    break

    # -----------------------------------------------
    #                  check_pif_json
    # -----------------------------------------------
    def check_pif_json(self):
        device = get_phone()
        if not device.rooted:
            return
        # check for presence of pif.json
        res, tmp = device.check_file(self.pif_json_path, True)
        if res == 1:
            self.pif_exists = True
            self.reload_pif_button.Enable(True)
            self.create_pif_button.SetLabel("Update pif.json")
            self.create_pif_button.SetToolTip(u"Update pif.json.")
        else:
            self.pif_exists = False
            self.reload_pif_button.Enable(False)
            self.create_pif_button.SetLabel("Create pif.json")
            self.create_pif_button.SetToolTip(u"Create pif.json.")
        self.ActivePifStcChange(None)

    # -----------------------------------------------
    #                  PifComboBox
    # -----------------------------------------------
    def PifComboBox(self, event):
        selected_label = event.GetString()
        selected_pif = next((pif for pif in self.favorite_pifs.values() if pif["label"] == selected_label), None)
        if selected_pif:
            pif_object = selected_pif["pif"]
            self.active_pif_stc.SetText(json.dumps(pif_object, indent=4))
        else:
            print("Selected Pif not found")

    # -----------------------------------------------
    #                  TestSelection
    # -----------------------------------------------
    def TestSelection(self, event):
        option = event.GetString()

        if option == "Play Integrity API Checker":
            print("Play Integrity API Checker option selected")
            self.pi_app = 'gr.nikolasspyr.integritycheck'

        elif option == "Simple Play Integrity Checker":
            print("Simple Play Integrity Checker option selected")
            self.pi_app = 'com.henrikherzig.playintegritychecker'

        elif option == "TB Checker":
            print("TB Checker option selected")
            self.pi_app = 'krypton.tbsafetychecker'

        elif option == "Play Store":
            print("Play Store option selected")
            self.pi_app = 'com.android.vending'

        elif option == "YASNAC":
            print("YASNAC option selected")
            self.pi_app = 'rikka.safetynetchecker'

    # -----------------------------------------------
    #                  __del__
    # -----------------------------------------------
    def __del__(self):
        pass

    # -----------------------------------------------
    #                  onClose
    # -----------------------------------------------
    def onClose(self, e):
        dialog_size = self.GetSize()
        dialog_x, dialog_y = dialog_size.GetWidth(), dialog_size.GetHeight()
        self.Parent.config.pif_width = dialog_x
        self.Parent.config.pif_height = dialog_y
        self.Close()

    # -----------------------------------------------
    #                  LoadReload
    # -----------------------------------------------
    def LoadReload(self, e):
        try:
            device = get_phone()
            if not device.rooted:
                return
            self._on_spin('start')
            config_path = get_config_path()
            pif_prop = os.path.join(config_path, 'tmp', 'pif.json')
            if self.reload_pif_button.Enabled:
                # pull the file
                res = device.pull_file(self.pif_json_path, pif_prop, True)
                if res != 0:
                    print("Aborting ...\n")
                    # puml("#red:Failed to pull pif.prop from the phone;\n}\n")
                    self._on_spin('stop')
                    return
            else:
                # we need to create one.
                with open(pif_prop, 'w') as file:
                    pass
            # get the contents of modified pif.json
            with open(pif_prop, 'r', encoding='ISO-8859-1', errors="replace") as f:
                contents = f.read()
                self.device_pif = contents
            self.active_pif_stc.SetValue(contents)

        except Exception as e:
            print(f"\n{datetime.now():%Y-%m-%d %H:%M:%S} ERROR: Exception during pip Load process.")
            traceback.print_exc()
        self._on_spin('stop')

    # -----------------------------------------------
    #                  CreatePifJson
    # -----------------------------------------------
    def CreatePifJson(self, e):
        self.create_update_pif()

    # -----------------------------------------------
    #                  UpdatePifJson
    # -----------------------------------------------
    def UpdatePifJson(self, e):
        self.create_update_pif()

    # -----------------------------------------------
    #                  create_update_pif
    # -----------------------------------------------
    def create_update_pif(self):
        device = get_phone()
        if not device.rooted:
            return

        self._on_spin('start')
        config_path = get_config_path()
        pif_prop = os.path.join(config_path, 'tmp', 'pif.json')

        json_data = self.active_pif_stc.GetValue()
        if json_data:
            try:
                data = json.loads(json_data)
            except Exception:
                try:
                    data = json5.loads(json_data)
                except Exception:
                    print(f"\n{datetime.now():%Y-%m-%d %H:%M:%S} ERROR: Not a valid json.")
                    return
        else:
            print(f"\n{datetime.now():%Y-%m-%d %H:%M:%S} ERROR: Not a valid json.")
            return

        # Save the data as normal JSON
        with open(pif_prop, 'w', encoding="ISO-8859-1", errors="replace", newline='\n') as f:
            json.dump(data, f, indent=4)

        # push the file
        res = device.push_file(pif_prop, self.pif_json_path, True)
        if res != 0:
            print("Aborting ...\n")
            # puml("#red:Failed to push pif.json from the phone;\n}\n")
            self._on_spin('stop')
            return -1

        self.device_pif = data

        print("Killing Google GMS  ...")
        res = device.perform_package_action(pkg='com.google.android.gms.unstable', action='killall')
        if res.returncode != 0:
            print("Error killing GMS.")
        else:
            print("Killing Google GMS succeeded.")

        self.check_pif_json()
        self.LoadReload(None)

        # Auto test Play Integrity
        if self.auto_check_pi_checkbox.IsEnabled() and self.auto_check_pi_checkbox.IsChecked():
            print("Auto Testing Play Integrity ...")
            self.PlayIntegrityCheck(None)
        self._on_spin('stop')

    # -----------------------------------------------
    #                  get_pi_app_coords
    # -----------------------------------------------
    def get_pi_app_coords(self, child=None):
        try:
            device = get_phone()
            if not device.rooted:
                return
            print(f"{datetime.now():%Y-%m-%d %H:%M:%S} Getting coordinates for {self.pi_app}")

            # pull view
            config_path = get_config_path()
            pi_app_xml = os.path.join(config_path, 'tmp', 'pi_app.xml')

            if self.pi_app == 'gr.nikolasspyr.integritycheck':
                return  device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "CHECK", False)

            elif self.pi_app == 'com.henrikherzig.playintegritychecker':
                return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Make Play Integrity Request", False)

            elif self.pi_app == 'krypton.tbsafetychecker':
                return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Run Play Integrity Check", False)

            elif self.pi_app == 'rikka.safetynetchecker':
                return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Run SafetyNet Attestation", False)

            elif self.pi_app == 'com.android.vending':
                if child == 'user':
                    # This needs custom handling, as there is no identifiable string to look for
                    return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "PixelFlasher_Playstore", True)
                if child == 'settings':
                    return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Settings", True)
                if child == 'general':
                    return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "General", True)
                if child == 'scroll':
                    return device.swipe_up()
                if child == 'developer_options':
                    return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Developer options", True)
                if child == 'test':
                    return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Check integrity", False)
                if child == 'dismiss':
                    return device.ui_action('/data/local/tmp/pi.xml', pi_app_xml, "Dismiss", False)

        except Exception:
            traceback.print_exc()

    # -----------------------------------------------
    #                  XiaomiPif
    # -----------------------------------------------
    def XiaomiPif(self, e):
        try:
            self._on_spin('start')
            xiaomi_pif = get_xiaomi_pif()
            self.console_stc.SetValue(xiaomi_pif)
        except Exception:
            traceback.print_exc()
        self._on_spin('stop')

    # -----------------------------------------------
    #                  FreemanPif
    # -----------------------------------------------
    def FreemanPif(self, e):
        try:
            device = get_phone()
            if not device:
                abilist = ''
            else:
                if not device.rooted:
                    return
                self._on_spin('start')
                keys = ['ro.product.cpu.abilist', 'ro.product.cpu.abi', 'ro.system.product.cpu.abilist', 'ro.vendor.product.cpu.abilist']
                abilist = get_first_match(device.props.property, keys)

            freeman_pif = get_freeman_pif(abilist)
            self.console_stc.SetValue(freeman_pif)
        except Exception:
            traceback.print_exc()
        self._on_spin('stop')

    # -----------------------------------------------
    #                  PlayIntegrityCheck
    # -----------------------------------------------
    def PlayIntegrityCheck(self, e):
        try:
            device = get_phone()
            if not device.rooted:
                return
            print(f"{datetime.now():%Y-%m-%d %H:%M:%S} User Pressed Play Integrity API Checker.")
            self._on_spin('start')

            if not self.insync:
                self.toast("Active pif not in sync", "WARNING! Device pif is not in sync with Active Pif contents.\nThe result will not be reflective of the Active pif you're viewing.")

            # We need to kill TB Checker , Play Store and YASNAC to make sure we read fresh values
            if self.pi_option.Selection in [2, 3, 4]:
                res = device.perform_package_action(self.pi_app, 'kill', False)

            # launch the app
            res = device.perform_package_action(self.pi_app, 'launch', False)
            if res == -1:
                print(f"Error: during launching app {self.pi_app}.")
                self._on_spin('stop')
                return -1

            # See if we have coordinates saved
            coords = self.coords.query_entry(device.id, self.pi_app)
            coord_dismiss = None
            if coords is None:
                if self.disable_uiautomator_checkbox.IsChecked():
                    print(f"WARNING! You have disabled using UIAutomator.\nPlease uncheck Disable UIAutomator checkbox if you want to enable UIAutomator usage.")
                    self._on_spin('stop')
                    return
                # For Play Store, we need to save multiple coordinates
                if self.pi_option.Selection == 3:
                    # Get coordinates for the first time
                    # user
                    coord_user = self.get_pi_app_coords(child='user')
                    if coord_user == -1:
                        print(f"Error: during tapping {self.pi_app} [user] screen.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
                    self.coords.update_nested_entry(device.id, self.pi_app, "user", coord_user)

                    # settings
                    coord_settings = self.get_pi_app_coords(child='settings')
                    if coord_settings == -1:
                        print(f"Error: during tapping {self.pi_app} [settings] screen.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
                    self.coords.update_nested_entry(device.id, self.pi_app, "settings", coord_settings)

                    # general
                    coord_general = self.get_pi_app_coords(child='general')
                    if coord_general == -1:
                        print(f"Error: during tapping {self.pi_app} [general] screen.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
                    self.coords.update_nested_entry(device.id, self.pi_app, "general", coord_general)
                    # page scroll
                    coord_scroll = self.get_pi_app_coords(child='scroll')
                    if coord_scroll == -1:
                        print(f"Error: during swipping {self.pi_app} [scroll] screen.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
                    self.coords.update_nested_entry(device.id, self.pi_app, "scroll", coord_scroll)
                    # Developer Options
                    coord_developer_options = self.get_pi_app_coords(child='developer_options')
                    if coord_developer_options == -1:
                        print(f"Error: during tapping {self.pi_app} [developer_options] screen.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
                    self.coords.update_nested_entry(device.id, self.pi_app, "developer_options", coord_developer_options)
                    # Check Integrity
                    coord_test = self.get_pi_app_coords(child='test')
                    if coord_test == -1:
                        print(f"Error: during tapping {self.pi_app} [Check Integrity] screen.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
                    self.coords.update_nested_entry(device.id, self.pi_app, "test", coord_test)
                    coords = coord_test
                else:
                    # Get coordinates for the first time
                    coords = self.get_pi_app_coords()
                    if coords is not None and coords != -1:
                        # update coords.json
                        self.coords.update_entry(device.id, self.pi_app, coords)
                    else:
                        print("Error: Could not get coordinates.")
                        if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                            del self.coords.data[device.id][self.pi_app]
                            self.coords.save_data()
                        self._on_spin('stop')
                        return -1
            elif self.pi_option.Selection == 3:
                coord_user = self.coords.query_nested_entry(device.id, self.pi_app, "user")
                coord_settings = self.coords.query_nested_entry(device.id, self.pi_app, "settings")
                coord_general = self.coords.query_nested_entry(device.id, self.pi_app, "general")
                coord_scroll = self.coords.query_nested_entry(device.id, self.pi_app, "scroll")
                coord_developer_options = self.coords.query_nested_entry(device.id, self.pi_app, "developer_options")
                coord_test = self.coords.query_nested_entry(device.id, self.pi_app, "test")
                coord_dismiss = self.coords.query_nested_entry(device.id, self.pi_app, "dismiss")
                if coord_user is None or coord_user == '' or coord_settings is None or coord_settings == '' or coord_general is None or coord_general == '' or coord_developer_options is None or coord_developer_options == '' or coord_test is None or coord_test == '':
                    print(f"\nError: coordinates for {self.pi_app} is missing from settings\nPlease run the test again so that PixelFlasher can try to get fresh new coordinates.")
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]
                        self.coords.save_data()
                    self._on_spin('stop')
                    return -1

                # user
                res = device.click(coord_user)
                if res == -1:
                    print(f"Error: during tapping {self.pi_app} [user] screen.")
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]
                        self.coords.save_data()
                    self._on_spin('stop')
                    return -1
                time.sleep(1)
                # settings
                res = device.click(coord_settings)
                if res == -1:
                    print(f"Error: during tapping {self.pi_app} [settings] screen.")
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]
                        self.coords.save_data()
                    self._on_spin('stop')
                    return -1
                time.sleep(1)
                # general
                res = device.click(coord_general)
                if res == -1:
                    print(f"Error: during tapping {self.pi_app} [general] screen.")
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]
                        self.coords.save_data()
                    self._on_spin('stop')
                    return -1
                time.sleep(1)
                res = device.swipe(coord_scroll)
                if res == -1:
                    print(f"Error: during swiping {self.pi_app} [scroll] screen.")
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]
                        self.coords.save_data()
                    self._on_spin('stop')
                    return -1
                time.sleep(1)
                # developer_options
                res = device.click(coord_developer_options)
                if res == -1:
                    print(f"Error: during tapping {self.pi_app} [developer_options] screen.")
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]
                        self.coords.save_data()
                    self._on_spin('stop')
                    return -1
                time.sleep(1)
                # test
                coords = coord_test

            # Click on coordinates
            res = device.click(coords)
            if res == -1:
                print(f"\nError: coordinates for {self.pi_app} is missing from settings\nPlease run the test again so that PixelFlasher can try to get fresh new coordinates.")
                if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                    del self.coords.data[device.id][self.pi_app]
                    self.coords.save_data()
                self._on_spin('stop')
                return -1

            # Skip Getting results if UIAutomator is disabled.
            if not self.disable_uiautomator_checkbox.IsChecked():
                # pull view
                config_path = get_config_path()
                pi_xml = os.path.join(config_path, 'tmp', 'pi.xml')
                time.sleep(5)
                res = device.ui_action('/data/local/tmp/pi.xml', pi_xml)
                if res == -1:
                    print(f"Error: during uiautomator {self.pi_app}.")
                    self._on_spin('stop')
                    return -1

                # extract result
                if self.pi_option.Selection == 0:
                    res = process_pi_xml_piac(pi_xml)
                if self.pi_option.Selection == 1:
                    res = process_pi_xml_spic(pi_xml)
                if self.pi_option.Selection == 2:
                    res = process_pi_xml_tb(pi_xml)
                if self.pi_option.Selection == 3:
                    res = process_pi_xml_ps(pi_xml)
                    # dismiss
                    if coord_dismiss is None or coord_dismiss == '' or coord_dismiss == -1:
                        coord_dismiss = self.get_pi_app_coords(child='dismiss')
                        if coord_dismiss == -1:
                            print(f"Error: getting coordinates for {self.pi_app} [dismiss] screen.")
                            if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                                del self.coords.data[device.id][self.pi_app]['dismiss']
                                self.coords.save_data()
                            self._on_spin('stop')
                        self.coords.update_nested_entry(device.id, self.pi_app, "dismiss", coord_dismiss)
                if self.pi_option.Selection == 4:
                    res = process_pi_xml_yasnac(pi_xml)

                if res == -1:
                    print(f"Error: during processing the response from {self.pi_app}.")
                    self._on_spin('stop')
                    return -1

                self.console_stc.SetValue('')
                if res is None or res == '':
                    if device.id in self.coords.data and self.pi_app in self.coords.data[device.id]:
                        del self.coords.data[device.id][self.pi_app]['dismiss']
                else:
                    self.console_stc.SetValue(res)

        except Exception:
            traceback.print_exc()
        self._on_spin('stop')


    # -----------------------------------------------
    #                  sort_prop
    # -----------------------------------------------
    def sort_prop(self, file_path):
        filename = os.path.basename(file_path)
        if filename == "build.prop":
            return 1
        elif filename == "system-build.prop":
            return 2
        elif filename == "system.prop":
            return 3
        elif filename == "product-build.prop":
            return 4
        elif filename == "product.prop":
            return 5
        elif filename == "vendor-build.prop":
            return 6
        elif filename == "vendor.prop":
            return 7
        else:
            return 999


    # -----------------------------------------------
    #                  ProcessBuildProp
    # -----------------------------------------------
    def process_dict(self, dict):
        try:
            # FINGERPRINT
            fp_ro_product_brand = ''
            fp_ro_product_name = ''
            fp_ro_product_device = ''
            fp_ro_build_version_release = ''
            fp_ro_build_id = ''
            fp_ro_build_version_incremental = ''
            fp_ro_build_type = ''
            fp_ro_build_tags = ''
            keys = ['ro.build.fingerprint', 'ro.system.build.fingerprint', 'ro.product.build.fingerprint', 'ro.vendor.build.fingerprint']
            ro_build_fingerprint = get_first_match(dict, keys)
            if ro_build_fingerprint:
                # Let's extract props from fingerprint in case we need them
                pattern = r'([^\/]*)\/([^\/]*)\/([^:]*):([^\/]*)\/([^\/]*)\/([^:]*):([^\/]*)\/([^\/]*)$'
                match = re.search(pattern, ro_build_fingerprint)
                if match and match.lastindex == 8:
                    fp_ro_product_brand = match[1]
                    fp_ro_product_name = match[2]
                    fp_ro_product_device = match[3]
                    fp_ro_build_version_release = match[4]
                    fp_ro_build_id = match[5]
                    fp_ro_build_version_incremental = match[6]
                    fp_ro_build_type = match[7]
                    fp_ro_build_tags = match[8]

            autofill = False
            if self.add_missing_keys_checkbox.IsChecked():
                device = get_phone()
                if device:
                    autofill = True
                else:
                    print("ERROR: Device is unavilable to add missing fields from device.")

            # PRODUCT
            keys = ['ro.product.name', 'ro.product.system.name', 'ro.product.product.name', 'ro.product.vendor.name', 'ro.vendor.product.name']
            ro_product_name = get_first_match(dict, keys)
            if (ro_product_name is None or ro_product_name == '') and fp_ro_product_name != '':
                debug(f"Properties for PRODUCT are not found, using value from FINGERPRINT: {fp_ro_product_name}")
                ro_product_name = fp_ro_product_name

            # DEVICE
            keys = ['ro.product.device', 'ro.product.system.device', 'ro.product.product.device', 'ro.product.vendor.device', 'ro.build.product', 'ro.vendor.product.device']
            ro_product_device = get_first_match(dict, keys)
            if (ro_product_device is None or ro_product_device == '') and fp_ro_product_device != '':
                debug(f"Properties for DEVICE are not found, using value from FINGERPRINT: {fp_ro_product_device}")
                ro_product_device = fp_ro_product_device

            # MANUFACTURER
            keys = ['ro.product.manufacturer', 'ro.product.system.manufacturer', 'ro.product.product.manufacturer', 'ro.product.vendor.manufacturer', 'ro.vendor.product.manufacturer']
            ro_product_manufacturer = get_first_match(dict, keys)
            if autofill and ro_product_manufacturer == '':
                ro_product_manufacturer = device.get_prop('ro.product.manufacturer')

            # BRAND
            keys = ['ro.product.brand', 'ro.product.system.brand', 'ro.product.product.brand', 'ro.product.vendor.brand', 'ro.vendor.product.brand']
            ro_product_brand = get_first_match(dict, keys)
            if (ro_product_brand is None or ro_product_brand == '') and fp_ro_product_brand != '':
                debug(f"Properties for BRAND are not found, using value from FINGERPRINT: {fp_ro_product_brand}")
                ro_product_brand = fp_ro_product_brand

            # MODEL
            keys = ['ro.product.model', 'ro.product.system.model', 'ro.product.product.model', 'ro.product.vendor.model', 'ro.vendor.product.model']
            ro_product_model = get_first_match(dict, keys)

            # SECURITY_PATCH
            keys = ['ro.build.version.security_patch', 'ro.vendor.build.security_patch']
            ro_build_version_security_patch = get_first_match(dict, keys)

            # FIRST_API_LEVEL
            keys = ['ro.product.first_api_level', 'ro.board.first_api_level', 'ro.board.api_level', 'ro.build.version.sdk', 'ro.system.build.version.sdk', 'ro.build.version.sdk', 'ro.system.build.version.sdk', 'ro.vendor.build.version.sdk', 'ro.product.build.version.sdk']
            ro_product_first_api_level = get_first_match(dict, keys)
            if ro_product_first_api_level and int(ro_product_first_api_level) > 32:
                ro_product_first_api_level = '32'

            # BUILD_ID
            keys = ['ro.build.id']
            ro_build_id = get_first_match(dict, keys)
            if (ro_build_id is None or ro_build_id == '') and fp_ro_build_id != '':
                debug(f"Properties for ID are not found, using value from FINGERPRINT: {fp_ro_build_id}")
                ro_build_id = fp_ro_build_id

            # RELEASE
            keys = ['ro.build.version.release']
            ro_build_version_release = get_first_match(dict, keys)
            if (ro_build_version_release is None or ro_build_version_release == '') and fp_ro_build_version_release != '':
                debug(f"Properties for RELEASE are not found, using value from FINGERPRINT: {fp_ro_build_version_release}")
                ro_build_version_release = fp_ro_build_version_release

            # INCREMENTAL
            keys = ['ro.build.version.incremental']
            ro_build_version_incremental = get_first_match(dict, keys)
            if (ro_build_version_incremental is None or ro_build_version_incremental == '') and fp_ro_build_version_incremental != '':
                debug(f"Properties for INCREMENTAL are not found, using value from FINGERPRINT: {fp_ro_build_version_incremental}")
                ro_build_version_incremental = fp_ro_build_version_incremental

            # TYPE
            keys = ['ro.build.type']
            ro_build_type = get_first_match(dict, keys)
            if (ro_build_type is None or ro_build_type == '') and fp_ro_build_type != '':
                debug(f"Properties for TYPE are not found, using value from FINGERPRINT: {fp_ro_build_type}")
                ro_build_type = fp_ro_build_type

            # TAGS
            keys = ['ro.build.tags']
            ro_build_tags = get_first_match(dict, keys)
            if (ro_build_tags is None or ro_build_tags == '') and fp_ro_build_tags != '':
                debug(f"Properties for TAGS are not found, using value from FINGERPRINT: {fp_ro_build_tags}")
                ro_build_tags = fp_ro_build_tags

            # VNDK_VERSION
            keys = ['ro.vndk.version', 'ro.product.vndk.version']
            ro_vndk_version = get_first_match(dict, keys)

            # Get any missing FINGERPRINT fields
            ffp_ro_product_brand = fp_ro_product_brand if fp_ro_product_brand != '' else ro_product_brand
            ffp_ro_product_name = fp_ro_product_name if fp_ro_product_name != '' else ro_product_name
            ffp_ro_product_device = fp_ro_product_device if fp_ro_product_device != '' else ro_product_device
            ffp_ro_build_version_release = fp_ro_build_version_release if fp_ro_build_version_release != '' else ro_build_version_release
            ffp_ro_build_id = fp_ro_build_id if fp_ro_build_id != '' else ro_build_id
            ffp_ro_build_version_incremental = fp_ro_build_version_incremental if fp_ro_build_version_incremental != '' else ro_build_version_incremental
            ffp_ro_build_type = fp_ro_build_type if fp_ro_build_type != '' else ro_build_type
            ffp_ro_build_tags = fp_ro_build_tags if fp_ro_build_tags != '' else ro_build_tags
            # Rebuild the FINGERPRINT
            ro_build_fingerprint = f"{ffp_ro_product_brand}/{ffp_ro_product_name}/{ffp_ro_product_device}:{ffp_ro_build_version_release}/{ffp_ro_build_id}/{ffp_ro_build_version_incremental}:{ffp_ro_build_type}/{ffp_ro_build_tags}"

            donor_data = {
                "PRODUCT": ro_product_name,
                "DEVICE": ro_product_device,
                "MANUFACTURER": ro_product_manufacturer,
                "BRAND": ro_product_brand,
                "MODEL": ro_product_model,
                "FINGERPRINT": ro_build_fingerprint,
                "SECURITY_PATCH": ro_build_version_security_patch
            }
            if self.advanced_props_support:
                donor_data["DEVICE_INITIAL_SDK_INT"] = ro_product_first_api_level
                donor_data["*api_level"] = ro_product_first_api_level
                donor_data["*.security_patch"] = ro_build_version_security_patch
                donor_data["ID"] = ro_build_id
                donor_data["*.build.id"] = ro_build_id
                donor_data["RELEASE"] = ro_build_version_release
                donor_data["INCREMENTAL"] = ro_build_version_incremental
                donor_data["TYPE"] = ro_build_type
                donor_data["TAGS"] = ro_build_tags
                donor_data["*.vndk_version"] = ro_vndk_version
                donor_data["VERBOSE_LOGS"] = "0"
            else:
                donor_data["FIRST_API_LEVEL"] = ro_product_first_api_level
                donor_data["BUILD_ID"] = ro_build_id
                donor_data["VNDK_VERSION"] = ro_vndk_version

            # Discard keys with empty values if the flag is set
            if self.advanced_props_support:
                modified_donor_data = {key: value for key, value in donor_data.items() if value != ""}
            else:
                modified_donor_data = donor_data

            return json.dumps(modified_donor_data, indent=4)

        except Exception as e:
            print(f"\n{datetime.now():%Y-%m-%d %H:%M:%S} ERROR: Exception in function process_dict.")
            traceback.print_exc()
            return ''

    # -----------------------------------------------
    #                  ProcessBuildProp
    # -----------------------------------------------
    def ProcessBuildProp(self, e):
        # sourcery skip: dict-assign-update-to-union
        print(f"{datetime.now():%Y-%m-%d %H:%M:%S} User pressed Process build.prop")
        wildcard = "Property files (*.prop)|*.prop|All files (*.*)|*.*"
        dialog = wx.FileDialog(self, "Choose property files to open", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_MULTIPLE)

        if dialog.ShowModal() == wx.ID_CANCEL:
            print("User cancelled file selection.")
            return

        paths = dialog.GetPaths()
        dialog.Destroy()
        sorted_paths = sorted(paths, key=self.sort_prop)

        print(f"Selected files: {sorted_paths}")

        try:
            self._on_spin('start')
            processed_dict = {}
            for pathname in reversed(sorted_paths):
                with open(pathname, 'r', encoding='ISO-8859-1', errors="replace") as f:
                    content = f.readlines()

                contentList = [x.strip().split('#')[0].split('=', 1) for x in content if '=' in x.split('#')[0]]
                contentDict = dict(contentList)

                # Update processed_dict with entries from the current file
                # In place Union operator below fails on Windows 2019 build, so use the update method instead.
                # processed_dict |= contentDict
                processed_dict.update(contentDict)

                # Apply the substitution to the values in processed_dict
                for k, v in contentDict.items():
                    for x in v.split('$')[1:]:
                        key = re.findall(r'\w+', x)[0]
                        v = v.replace(f'${key}', processed_dict[key])
                    processed_dict[k] = v.strip()

            donor_json = self.process_dict(processed_dict)
            self.console_stc.SetValue(donor_json)
            # print(donor_json)

            # Auto Push pif.json
            if self.auto_push_pif_checkbox.IsEnabled() and self.auto_push_pif_checkbox.IsChecked():
                self.active_pif_stc.SetValue(self.console_stc.GetValue())
                self.UpdatePifJson(None)

                # Auto test Play Integrity
                if self.auto_check_pi_checkbox.IsEnabled() and self.auto_check_pi_checkbox.IsChecked():
                    print("Auto Testing Play Integrity ...")
                    self.PlayIntegrityCheck(None)

        except Exception:
            print(f"Cannot process file: '{pathname}'.")
            traceback.print_exc()
        self._on_spin('stop')

    # -----------------------------------------------
    #                  ConsoleStcChange
    # -----------------------------------------------
    def ConsoleStcChange(self, event):
        try:
            json_data = self.console_stc.GetValue()

            if json_data:
                try:
                    json.loads(json_data)
                    self.paste_up.Enable(True)
                except Exception:
                    try:
                        json5.loads(json_data)
                        self.paste_up.Enable(True)
                    except Exception:
                        self.paste_up.Enable(False)
            else:
                self.paste_up.Enable(False)

        except Exception:
            traceback.print_exc()
        if event:
            event.Skip()

    # -----------------------------------------------
    #                  ActivePifStcChange
    # -----------------------------------------------
    def ActivePifStcChange(self, event):
        try:
            json_data = self.active_pif_stc.GetValue()

            if not self.enable_buttons:
                self.create_pif_button.Enable(False)
                return

            if json_data:
                try:
                    json.loads(json_data)
                    self.paste_down.Enable(True)
                    self.reprocess.Enable(True)
                    self.create_pif_button.Enable(True)
                    self.favorite_pif_button.Enable(True)
                except Exception:
                    try:
                        json5.loads(json_data)
                        self.paste_down.Enable(False)
                        self.reprocess.Enable(True)
                        self.create_pif_button.Enable(True)
                        self.favorite_pif_button.Enable(True)
                    except Exception:
                        self.create_pif_button.Enable(False)
                        self.reprocess.Enable(False)
                        self.paste_down.Enable(False)
                        self.favorite_pif_button.Enable(False)
            else:
                self.paste_down.Enable(False)
                self.create_pif_button.Enable(False)
                self.reprocess.Enable(False)
                self.favorite_pif_button.Enable(False)

            if json_data != self.device_pif:
                self.pif_modified_image.SetBitmap(images.alert_red_24.GetBitmap())
                self.pif_modified_image.SetToolTip(u"The contents is different than what is currently on the device.\nUpdate pif.json before testing.")
                self.insync = False
            else:
                self.pif_modified_image.SetBitmap(images.alert_gray_24.GetBitmap())
                self.pif_modified_image.SetToolTip(u"Active pif is not modified.")
                self.insync = True

            if self.create_pif_button.Enabled and self.favorite_pif_button.Enabled:
                pif_hash = json_hexdigest(json_data)
                if pif_hash in self.favorite_pifs:
                    self.favorite_pif_button.SetBitmap(images.heart_red_24.GetBitmap())
                    self.favorite_pif_button.SetToolTip(u"Active pif is saved in favorites.")
                    self.update_combo_box(pif_hash)
                else:
                    self.favorite_pif_button.SetBitmap(images.heart_gray_24.GetBitmap())
                    self.favorite_pif_button.SetToolTip(u"Active pif is not saved in favorites.")

        except Exception:
            traceback.print_exc()
        if event:
            event.Skip()

    # -----------------------------------------------
    #                  update_combo_box
    # -----------------------------------------------
    def update_combo_box(self, pif_hash=None):
        try:
            pif_labels = [pif["label"] for pif in self.favorite_pifs.values()]
            self.pif_combo_box.SetItems(pif_labels)

            # temporarily unbind so that we don't trigger another ActivePifStcChange with the combo box selection
            self.active_pif_stc.Unbind(wx.stc.EVT_STC_CHANGE, handler=self.ActivePifStcChange)
            # Make the combo box selection
            if pif_hash is None:
                self.pif_combo_box.SetSelection(-1)
            else:
                label = self.favorite_pifs[pif_hash]["label"]
                index = self.pif_combo_box.FindString(label)
                if index != wx.NOT_FOUND:
                    self.pif_combo_box.SetSelection(index)
                else:
                    self.pif_combo_box.SetSelection(-1)
            # rebind the event
            self.active_pif_stc.Bind(wx.stc.EVT_STC_CHANGE, self.ActivePifStcChange)

        except Exception:
            traceback.print_exc()

    # -----------------------------------------------
    #                  PasteUp
    # -----------------------------------------------
    def PasteUp(self, event):
        self.active_pif_stc.SetValue(self.console_stc.GetValue())
        event.Skip()

    # -----------------------------------------------
    #                  PasteDown
    # -----------------------------------------------
    def PasteDown(self, event):
        self.console_stc.SetValue(self.active_pif_stc.GetValue())
        event.Skip()


    # -----------------------------------------------
    #                  load_json_with_rules
    # -----------------------------------------------
    def load_json_with_rules(self, json_str, discard_empty_keys=False):
        # Load JSON string into a dictionary
        data = json5.loads(json_str)

        # Define the mapping rules
        mapping_rules = {
            "MANUFACTURER": "ro.product.manufacturer",
            "MODEL": "ro.product.model",
            "BRAND": "ro.product.brand",
            "PRODUCT": "ro.product.name",
            "DEVICE": "ro.product.device",
            "FINGERPRINT": "ro.build.fingerprint",
            "SECURITY_PATCH": "ro.build.version.security_patch",
            "*.security_patch": "ro.build.version.security_patch",
            "FIRST_API_LEVEL": "ro.product.first_api_level",
            "*api_level": "ro.product.first_api_level",
            "BUILD_ID": "ro.build.id",
            "ID": "ro.build.id",
            "VNDK_VERSION": "ro.vndk.version",
            "*.vndk_version": "ro.vndk.version",
            "INCREMENTAL": "ro.build.version.incremental",
            "TYPE": "ro.build.type",
            "TAGS": "ro.build.tags"
        }

        # Create a new dictionary with the modified keys
        modified_data = {mapping_rules.get(key, key): value for key, value in data.items()}

        # Discard keys with empty values if the flag is set
        if discard_empty_keys:
            modified_data = {key: value for key, value in modified_data.items() if value != ""}

        return modified_data

    # -----------------------------------------------
    #                  ReProcess
    # -----------------------------------------------
    def ReProcess(self, event):
        try:
            self._on_spin('start')
            print("Reprocessing Active Pif content ...")
            self._on_spin('start')
            active_pif = self.active_pif_stc.GetValue()
            processed_dict = self.load_json_with_rules(active_pif, self.advanced_props_support)
            donor_json = self.process_dict(processed_dict)
            self.console_stc.SetValue(donor_json)

        except Exception:
            traceback.print_exc()
        self._on_spin('stop')
        if event:
            event.Skip()

    # -----------------------------------------------
    #                  Favorite
    # -----------------------------------------------
    def Favorite(self, event):
        try:
            active_pif = self.active_pif_stc.GetValue()
            pif_hash = json_hexdigest(active_pif)
            if pif_hash in self.favorite_pifs:
                # Delete from favorites
                del self.favorite_pifs[pif_hash]
                pif_hash = None
                self.update_combo_box()
                # self.pif_combo_box.SetSelection(-1)
            else:
                # Add to favorites
                dialog = wx.TextEntryDialog(None, "Enter a label:", "Save Pif to Favorites")
                result = dialog.ShowModal()
                if result == wx.ID_OK:
                    label = dialog.GetValue()
                    print("Label:", label)
                    self.favorite_pifs.setdefault(pif_hash, {})["label"] = label
                    self.favorite_pifs.setdefault(pif_hash, {})["date_added"] = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
                    self.favorite_pifs.setdefault(pif_hash, {})["pif"] = json.loads(active_pif)
                    dialog.Destroy()
                elif result == wx.ID_CANCEL:
                    print("Dialog canceled")
                    dialog.Destroy()
                    return

            set_favorite_pifs(self.favorite_pifs)

            with open(get_favorite_pifs_file_path(), "w", encoding='ISO-8859-1', errors="replace") as f:
                json.dump(self.favorite_pifs, f, indent=4)

            # self.update_combo_box(pif_hash)
            self.ActivePifStcChange(None)

        except Exception:
            traceback.print_exc()
        if event:
            event.Skip()

    # -----------------------------------------------
    #                  ImportFavorites
    # -----------------------------------------------
    def ImportFavorites(self, e):
        try:
            with wx.DirDialog(self, "Select folder to Import Pifs", style=wx.DD_DEFAULT_STYLE) as folderDialog:
                if folderDialog.ShowModal() == wx.ID_CANCEL:
                    print("User cancelled folder selection.")
                    return
                selected_folder = folderDialog.GetPath()

            self._on_spin('start')
            pif_files = [file for file in os.listdir(selected_folder) if file.endswith(".json")]
            for pif_file in pif_files:
                with open(os.path.join(selected_folder, pif_file), 'r', encoding="ISO-8859-1", errors="replace") as f:
                    data = json5.load(f)
                with contextlib.suppress(KeyError):
                    brand = data['BRAND']
                with contextlib.suppress(KeyError):
                    model = data['MODEL']
                label = f"{brand} {model}"
                pif_data = json.dumps(data, indent=4)
                pif_hash = json_hexdigest(pif_data)
                # Add to favorites
                print(f"Importing: {label} ...")
                self.favorite_pifs.setdefault(pif_hash, {})["label"] = label
                self.favorite_pifs.setdefault(pif_hash, {})["date_added"] = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
                self.favorite_pifs.setdefault(pif_hash, {})["pif"] = json.loads(pif_data)
                wx.YieldIfNeeded()

            set_favorite_pifs(self.favorite_pifs)
            with open(get_favorite_pifs_file_path(), "w", encoding='ISO-8859-1', errors="replace") as f:
                json.dump(self.favorite_pifs, f, indent=4)

            # self.update_combo_box(pif_hash)
            self.update_combo_box(None)

        except Exception:
            traceback.print_exc()
        self._on_spin('stop')

    # -----------------------------------------------
    #                  _on_spin
    # -----------------------------------------------
    def _on_spin(self, state):
        wx.YieldIfNeeded()
        if state == 'start':
            self.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
            self.Parent._on_spin('start')
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))
            self.Parent._on_spin('stop')

    # -----------------------------------------------
    #                  onResize
    # -----------------------------------------------
    def onResize(self, event):
        self.resizing = True
        stc_size = self.active_pif_stc.GetSize()
        x = stc_size.GetWidth()
        self.active_pif_stc.SetScrollWidth(x - 30)
        self.console_stc.SetScrollWidth(x - 30)

        self.Layout()
        if event:
            event.Skip(True)

    # -----------------------------------------------
    #                  toast
    # -----------------------------------------------
    def toast(self, title, message):
        if self.config.show_notifications:
            notification = wx.adv.NotificationMessage(title, message, parent=None, flags=wx.ICON_INFORMATION)
            notification.SetIcon(images.Icon_256.GetIcon())
            notification.Show()

