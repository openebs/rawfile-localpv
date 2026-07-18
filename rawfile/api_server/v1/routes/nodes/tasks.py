from api_server.v1.models import (
    Task,
    TasksList,
)
from fastapi import APIRouter, HTTPException, status
from internal import internal_pb2
from orchestrator.k8s import NodeUnavailableError, node_ip_mapping
from utils.remote import get_internal_grpc_stub, internal_auth_metadata

router = APIRouter()


@router.get("")
async def get_node_tasks(node_name: str) -> TasksList:
    try:
        ip = node_ip_mapping.get_node_ip(node_name)
        stub = get_internal_grpc_stub(ip, aio=True)
        response = await stub.GetNodeTasks(
            internal_pb2.GetNodeTasksRequest(), metadata=[internal_auth_metadata()]
        )
        return {
            task_id: Task(
                args=list(task_data.args or []),
                task=task_data.task,
                kwargs=task_data.kwargs,
                retry_count=task_data.retry_count,
                state=task_data.state,
            )
            for task_id, task_data in response.tasks
        }

    except NodeUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selected Node {node_name} Not found",
        )


@router.get("/{task_id}")
async def get_node_single_task(node_name: str, task_id: str) -> Task:
    try:
        ip = node_ip_mapping.get_node_ip(node_name)
        stub = get_internal_grpc_stub(ip, aio=True)
        response = await stub.GetNodeTasks(
            internal_pb2.GetNodeTasksRequest(), metadata=[internal_auth_metadata()]
        )
        task_data = response.tasks.get(task_id, None)
        if not task_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Selected task {task_id} not found",
            )
        return Task(
            args=task_data.args,
            task=task_data.task,
            kwargs=task_data.kwargs,
            retry_count=task_data.retry_count,
            state=task_data.state,
        )

    except NodeUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Selected Node {node_name} Not found",
        )
