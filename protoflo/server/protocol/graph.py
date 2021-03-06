from ...graph import Graph

import copy

class GraphProtocol (object):
	def __init__ (self, transport):
		self.transport = transport
		self.graphs = {}

	def send (self, topic, payload, context):
		self.transport.send('graph', topic, payload, context)

	def receive (self, topic, payload, context):
		if topic == 'clear':
			return self.initGraph(payload, context)

		try:
			# Find locally stored graph by ID
			graph = self.resolveGraph(payload)

			# Run command
			# FIXME: convert this to a dictionary
			# FIMXE: add addgroup, removegroup, renamegroup, changegroup
			if topic == 'addnode':         return self.addNode       (graph, payload, context)
			elif topic == 'removenode':    return self.removeNode    (graph, payload, context)
			elif topic == 'renamenode':    return self.renameNode    (graph, payload, context)
			elif topic == 'changenode':    return self.changeNode    (graph, payload, context)
			elif topic == 'addedge':       return self.addEdge       (graph, payload, context)
			elif topic == 'removeedge':    return self.removeEdge    (graph, payload, context)
			elif topic == 'changeedge':    return self.changeEdge    (graph, payload, context)
			elif topic == 'addinitial':    return self.addInitial    (graph, payload, context)
			elif topic == 'removeinitial': return self.removeInitial (graph, payload, context)
			elif topic == 'addinport':     return self.addInport     (graph, payload, context)
			elif topic == 'removeinport':  return self.removeInport  (graph, payload, context)
			elif topic == 'renameinport':  return self.renameInport  (graph, payload, context)
			elif topic == 'addoutport':    return self.addOutport    (graph, payload, context)
			elif topic == 'removeoutport': return self.removeOutport (graph, payload, context)
			elif topic == 'renameoutport': return self.renameOutport (graph, payload, context)

		except Error as e:
			self.send('error', e, context)
			return

	def resolveGraph (self, payload):
		if "graph" not in payload:
			raise Error('No graph specified')

		if payload["graph"] not in self.graphs:
			raise Error('Requested graph not found')

		return self.graphs[payload["graph"]]

	def initGraph (self, payload, context):
		if "id" not in payload:
			raise Error('No graph ID provided')

		if "name" not in payload:
			payload["name"] = 'NoFlo runtime'

		graph = Graph(payload["name"])

		fullName = payload["id"]
		if "library" in payload:
			graph.properties["library"] = payload["library"]
			fullName = payload["library"] + "/" + fullName

		# Pass the project baseDir
		#graph.baseDir = self.transport.options.baseDir

		self.subscribeGraph(payload["id"], graph, context)

		if "main" not in payload:
			# Register to component loading
			self.transport.component.registerGraph(fullName, graph, context)

		self.graphs[payload["id"]] = graph
		self.send('clear', payload, context)

	def subscribeGraph (self, id, graph, context):
		@graph.on('addNode')
		def subscribeGraphHandler_addNode (data):
			node = copy.deepcopy(data["node"])
			node["graph"] = id
			self.send('addnode', node, context)

		@graph.on('removeNode')
		def subscribeGraphHandler_removeNode (data):
			node = copy.deepcopy(data["node"])
			node["graph"] = id
			self.send('removenode', node, context)

		@graph.on('renameNode')
		def subscribeGraphHandler_renameNode (data):
			self.send('renamenode', {
				"from": data["old"],
				"to": data["new"],
				"graph": id
			}, context)

		@graph.on('changeNode')
		def subscribeGraphHandler_changeNode (data):
			node = copy.deepcopy(data["node"])
			node["graph"] = id
			# the nodejs runtime does not provide 'component' to changenode,
			# but does to removenode. we will immitate this for now.
			# FIXME: resolve this with the noflojs team
			comp = node.pop('component')
			self.send('changenode', node, context)

		@graph.on('addEdge')
		def subscribeGraphHandler_addEdge (data):
			edge = copy.deepcopy(data["edge"])
			edge["graph"] = id

			if edge["src"]["index"] is None:
				del edge["src"]["index"]

			if edge["tgt"]["index"] is None:
				del edge["tgt"]["index"]

			self.send('addedge', edge, context)

		@graph.on('removeEdge')
		def subscribeGraphHandler_removeEdge (data):
			edge = copy.deepcopy(data["edge"])
			edge["graph"] = id

			if edge["src"]["index"] is None:
				del edge["src"]["index"]

			if edge["tgt"]["index"] is None:
				del edge["tgt"]["index"]

			self.send('removeedge', edge, context)

		@graph.on('changeEdge')
		def subscribeGraphHandler_changeEdge (data):
			edge = copy.deepcopy(data["edge"])
			edge["graph"] = id

			if edge["src"]["index"] is None:
				del edge["src"]["index"]

			if edge["tgt"]["index"] is None:
				del edge["tgt"]["index"]

			self.send('changeedge', edge, context)

		@graph.on('addInitial')
		def subscribeGraphHandler_addInitial (data):
			iip = copy.deepcopy(data["edge"])
			iip["graph"] = id

			if iip["tgt"]["index"] is None:
				del iip["tgt"]["index"]

			self.send('addinitial', iip, context)

		@graph.on('removeInitial')
		def subscribeGraphHandler_removeInitial (data):
			iip = copy.deepcopy(data["edge"])
			iip["graph"] = id

			if iip["tgt"]["index"] is None:
				del iip["tgt"]["index"]

			self.send('removeinitial', iip, context)

	def addNode (self, graph, payload, context):
		graph.nodes.add(**args(payload, ["id", "component", "metadata"], 2))

	def removeNode (self, graph, payload, context):
		graph.nodes.remove(**args(payload, ["id"], True))

	def renameNode (self, graph, payload, context):
		graph.nodes.rename(*args(payload, ["from", "to"], True, asList = True))

	def changeNode (self, graph, payload, context):
		graph.nodes.setMetadata(**args(payload, ["id", "metadata"], True))

	def addEdge (self, graph, payload, context):
		graph.edges.addIndex(*args(
			payload, 
			["src.node", "src.port", "src.index", "tgt.node", "tgt.port", "tgt.index", "metadata"], 
			["src.node", "src.port", "tgt.node", "tgt.port"],
			asList = True
		))

	def removeEdge (self, graph, payload, context):
		graph.edges.remove(*args(payload, ["src.node", "src.port", "tgt.node", "tgt.port"], 1, asList = True))

	def changeEdge (self, graph, payload, context):
		graph.edges.setMetadata(*args(
			payload, 
			["src.node", "src.port", "tgt.node", "tgt.port", "metadata"], 
			True,
			asList = True
		))

	def addInitial (self, graph, payload, context):
		graph.initials.addIndex(**args(payload, ["src.data", "tgt.node", "tgt.port", "tgt.index", "metadata"], 3))

	def removeInitial (self, graph, payload, context):
		graph.initials.remove(**args(payload, ["tgt.node", "tgt.port"], 1))

	def addInport (self, graph, payload, context):
		# FIXME: adding a port to a graph is different than adding one to a component
		# (because a port on a graph is just a public label for a port on a component
		# within the graph) yet this code attempts to treat it the same.
		graph.inports.add(**args(payload, ["public", "node", "port", "metadata"], 3))

	def removeInport (self, graph, payload, context):
		# FIXME: see addInport
		graph.inports.remove(**args(payload, "public", True, 'Missing exported inport name'))

	def renameInport (self, graph, payload, context):
		# FIXME: see addInport
		graph.inports.rename(**args(payload, ["from", "to"], True))

	def addOutport (self, graph, payload, context):
		# FIXME: see addInport
		graph.outports.add(**args(payload, ["public", "node", "port", "metadata"], 3))

	def removeOutport (self, graph, payload, context):
		# FIXME: see addInport
		graph.outports.remove(**args(payload, "public", True, 'Missing exported outport name'))

	def renameOutport (self, graph, payload, context):
		# FIXME: see addInport
		graph.outports.rename(**args(payload, ["from", "to"], True))

def args (payload, keys, required = None, errorMsg = None, asList = False):
	new = [] if asList else {}
	keys = list(keys)

	if required in (None, False):
		# no keys
		required = []
	elif required is True:
		# all keys
		required = keys
	elif isinstance(required, int):
		# range of keys
		required = keys[:required]
	else:
		assert isinstance(required, list)

	def set (key, value):
		if asList:
			new.append(value)
		else:
			new[key] = value

	for key in keys:
		try:
			child = None

			if "." in key:
				parent, child = key.split(".", 1)
				set(child, payload[parent][child])
			else:
				set(key, payload[key])

		except (KeyError, TypeError):
			if key in required:
				raise Error(errorMsg or ("Required parameter '%s' not supplied" % key))
			else:
				set(child or key, None)

	return new

class Error (Exception):
	pass
