import ipywidgets as ipyw
from traitlets import Unicode, CBytes # Traitlet needed to add synced attributes to the widget.

class FileWidget(ipyw.DOMWidget):
    _view_name = Unicode('FilePickerView').tag(sync=True)
    _view_module = Unicode('filepicker').tag(sync=True)

    # value = Unicode().tag(sync=True)
    value = Unicode().tag(sync=True)
    filename = Unicode().tag(sync=True)

    def __init__(self, **kwargs):
        """Constructor"""
        ipyw.DOMWidget.__init__(self, **kwargs) # Call the base.

        # Allow the user to register error callbacks with the following signatures:
        #    callback()
        #    callback(sender)
        self.errors = ipyw.CallbackDispatcher(accepted_nargs=[0, 1])

        # Listen for custom msgs
        self.on_msg(self._handle_custom_msg)

    def _handle_custom_msg(self, content):
        """Handle a msg from the front-end.

        Parameters
        ----------
        content: dict
            Content of the msg."""
        if 'event' in content and content['event'] == 'error':
            self.errors()
            self.errors(self)
