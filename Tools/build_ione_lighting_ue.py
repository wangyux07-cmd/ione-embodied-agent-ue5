"""Build editable UI-domain materials for Ione's authored 2D scene layers."""
import unreal

E = unreal.MaterialEditingLibrary
PATH = '/Game/UI/Materials'
tools = unreal.AssetToolsHelpers.get_asset_tools()

PORTRAIT = r'''
float4 p = Texture2DSample(Portrait, PortraitSampler, UV);
float2 face = float2(.505, .133);
float cheek = exp(-dot((UV-float2(.555,.139))/float2(.052,.052),(UV-float2(.555,.139))/float2(.052,.052)));
float jaw = exp(-dot((UV-float2(.485,.173))/float2(.08,.019),(UV-float2(.485,.173))/float2(.08,.019)));
float faceShade = exp(-dot((UV-float2(.46,.145))/float2(.048,.05),(UV-float2(.46,.145))/float2(.048,.05)));
float leftCoat = exp(-dot((UV-float2(.32,.44))/float2(.12,.23),(UV-float2(.32,.44))/float2(.12,.23)));
float rightCoat = exp(-dot((UV-float2(.67,.48))/float2(.15,.25),(UV-float2(.67,.48))/float2(.15,.25)));
float nose = exp(-dot((UV-float2(.515,.143))/float2(.012,.022),(UV-float2(.515,.143))/float2(.012,.022)));
float sleeveY = PoseIndex < .5 ? .25 : PoseIndex < 1.5 ? .32 : PoseIndex < 2.5 ? .23 : .31;
float sleeveX = PoseIndex < .5 ? .71 : PoseIndex < 1.5 ? .83 : PoseIndex < 2.5 ? .70 : .65;
float sleeve = exp(-dot((UV-float2(sleeveX,sleeveY))/float2(.12,.08),(UV-float2(sleeveX,sleeveY))/float2(.12,.08)));
float leg = exp(-dot((UV-float2(.64,.83))/float2(.12,.16),(UV-float2(.64,.83))/float2(.12,.16)));
float edgeA = Texture2DSample(Portrait,PortraitSampler,UV-float2(.006,0)).a;
float rim = saturate(p.a-edgeA)*smoothstep(.8,.1,UV.y);
float shade = .80 - .21*leftCoat - .12*jaw - .17*faceShade;
float warm = (.26*cheek+.07*nose+.21*rightCoat+.16*sleeve+.13*leg)*Lamp;
float3 color = p.rgb*shade + p.rgb*float3(1.0,.63,.31)*warm;
color += float3(.025,.04,.045)*rim;
return float4(saturate(color),p.a);
'''

SHADOW = r'''
float a=0;
for(int x=-2;x<=2;x++)for(int y=-2;y<=2;y++)
 a+=Texture2DSample(Portrait,PortraitSampler,UV+float2(x*.006,y*.004)).a/25.;
return float4(.018,.024,.025,a*.22*Lamp);
'''

DIALOGUE = r'''
float edge = smoothstep(0,.05,UV.x)*smoothstep(1,.94,UV.x);
float grain = frac(sin(dot(floor(UV*float2(900,260)),float2(12.9898,78.233)))*43758.5453);
float contour = .025 + .008*sin(UV.x*39)+.004*sin(UV.x*143);
float body = smoothstep(contour,contour+.018,UV.y)*smoothstep(.998,.94,UV.y)*edge;
float borderInk = (1-smoothstep(.001,.004,abs(UV.y-contour-.018)))*edge;
float lower = (1-smoothstep(.001,.003,abs(UV.y-.735)))*edge*.18;
float alpha = body*(.64+.06*grain)+borderInk*.40+lower;
float3 rgb = lerp(float3(.035,.065,.069),float3(.50,.37,.23),saturate(borderInk+lower));
return float4(rgb,saturate(alpha));
'''

GLOW = r'''
float2 q=(UV-float2(.5,.42))*float2(1,1.15);
float halo=exp(-dot(q,q)*18);
float desk=exp(-dot((UV-float2(.5,.78))*float2(1.2,5),(UV-float2(.5,.78))*float2(1.2,5))*9);
return float4(.72,.42,.16,(halo*.09+desk*.055)*Lamp);
'''

for name, code, textured in [('M_IonePortraitLight_UI',PORTRAIT,True),
                              ('M_IoneBackShadow_UI',SHADOW,True),
                              ('M_IoneDialogue_UI',DIALOGUE,False),
                              ('M_IoneLampGlow_UI',GLOW,False)]:
    mat = unreal.load_asset(PATH+'/'+name)
    if mat is None:
        mat = tools.create_asset(name,PATH,unreal.Material,unreal.MaterialFactoryNew())
    else:
        E.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_UI)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    custom = E.create_material_expression(mat,unreal.MaterialExpressionCustom)
    custom.set_editor_property('code',code)
    custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    names=['UV','Lamp','PoseIndex']+(['Portrait'] if textured else [])
    inputs=[]
    for n in names:
        item=unreal.CustomInput()
        item.set_editor_property('input_name',n)
        inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    uv=E.create_material_expression(mat,unreal.MaterialExpressionTextureCoordinate)
    assert E.connect_material_expressions(uv,'',custom,'UV')
    for parameter,default in [('Lamp',1.0),('PoseIndex',0.0)]:
        node=E.create_material_expression(mat,unreal.MaterialExpressionScalarParameter)
        node.set_editor_property('parameter_name',parameter)
        node.set_editor_property('default_value',default)
        assert E.connect_material_expressions(node,'',custom,parameter)
    if textured:
        tex=E.create_material_expression(mat,unreal.MaterialExpressionTextureObjectParameter)
        tex.set_editor_property('parameter_name','Portrait')
        tex.set_editor_property('texture',unreal.load_asset('/Game/Character/Performance2D/Ione_Listen_Front'))
        assert E.connect_material_expressions(tex,'',custom,'Portrait')
    for alpha,prop in [(False,unreal.MaterialProperty.MP_EMISSIVE_COLOR),(True,unreal.MaterialProperty.MP_OPACITY)]:
        mask=E.create_material_expression(mat,unreal.MaterialExpressionComponentMask)
        for ch in ['r','g','b']: mask.set_editor_property(ch,not alpha)
        mask.set_editor_property('a',alpha)
        assert E.connect_material_expressions(custom,'',mask,'')
        assert E.connect_material_property(mask,'',prop)
    E.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    unreal.log('Ione UI material saved: '+name)
