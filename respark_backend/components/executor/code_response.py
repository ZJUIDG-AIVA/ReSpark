from typing import Any, Dict, List, Optional, Union

class CodeExecutorResponse:
    """Response from a visualization execution"""

    status: bool  # True if successful
    code: str  # code used to generate the visualization
    raster: Optional[str|None]  # base64 encoded image
    url: Optional[str|None] # base64 url
    calculated_result: Optional[str|None]
    json_result: Optional[dict|None]
    error: Optional[str|None]  # error message if status is False
    ex_locals: Optional[str|None]


    def __init__(
            self, 
            status: bool, 
            code: str,
            raster: Optional[str|None] = None,
            url: Optional[str|None] = None, 
            calculated_result: Optional[str|None] = None, 
            json_result: Optional[dict|None] = None, 
            error: Optional[str|None] = None,
            ex_locals: Optional[str|None] = None,
        ):
        self.status = status
        self.raster = raster
        self.code = code
        self.url = url
        self.calculated_result = calculated_result
        self.json_result = json_result
        self.error = error
        self.ex_locals = ex_locals


    def _repr_mimebundle_(self, include=None, exclude=None):
        bundle = {"text/plain": self.code}
        if self.raster is not None:
            bundle["image/png"] = self.raster

        return bundle